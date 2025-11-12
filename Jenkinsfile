pipeline {
  agent any
  environment {
    REGISTRY = "registry.local:5000"
    IMAGE = "myapp"
    SONAR_HOST = "http://localhost:9000"
    FLASK_PORT = "8888"  // Port utilisé pour Flask et tests
  }
  parameters {
    string(name: 'VERSION', defaultValue: "0.1.0-${env.BUILD_NUMBER}", description: 'Tag image')
    booleanParam(name: 'AUTO_PROMOTE', defaultValue: false, description: 'Promote automatiquement vers qualif/prod')
  }
  stages {
    stage('Checkout') { steps { checkout scm } }

    stage('Unit Tests') { 
      steps { 
        sh '''
          # Créer et activer le virtualenv
          python3 -m venv venv
          . venv/bin/activate

          # Installer les dépendances
          pip install --upgrade pip
          pip install -r requirements.txt

          # Lancer Flask sur le port 8888 en arrière-plan
          export FLASK_APP=app.py
          flask run --host=127.0.0.1 --port=$FLASK_PORT &
          FLASK_PID=$!

          # Attendre que Flask démarre
          sleep 5

          # Lancer les tests
          pytest -q || true

          # Arrêter Flask après tests
          kill $FLASK_PID
        ''' 
      } 
    }

      stage('SonarQube Analysis') {
  steps {
    script {
      echo "🔍 Lancement de l'analyse SonarQube..."
      def sonarHost = "http://172.17.0.1:9000"

      withSonarQubeEnv('My SonarQube Server') {
        withCredentials([string(credentialsId: 'SONAR_TOKEN', variable: 'SONAR_TOKEN')]) {
          sh """
            set -e
            if command -v sonar-scanner >/dev/null 2>&1; then
              echo '➡️ Exécution du scanner local...'
              sonar-scanner \
                -Dsonar.projectKey=my-app \
                -Dsonar.sources=. \
                -Dsonar.host.url=${sonarHost} \
                -Dsonar.login=$SONAR_TOKEN
            else
              echo '🐳 Exécution du scanner via Docker...'
              docker run --rm \
                -v "\$PWD":/usr/src \
                sonarsource/sonar-scanner-cli \
                -Dsonar.projectKey=my-app \
                -Dsonar.sources=/usr/src \
                -Dsonar.host.url=${sonarHost} \
                -Dsonar.login=$SONAR_TOKEN
            fi
          """
        }
      }
    }
  }
}


    
    stage('Quality Gate') {
      steps {
        timeout(time: 5, unit: 'MINUTES') {
          waitForQualityGate abortPipeline: true
        }
      }
    }


    stage('Build Docker Image') { 
      steps { 
        script { 
          IMAGE_TAG = "${env.REGISTRY}/${env.IMAGE}:${params.VERSION}"
          sh "docker build -t ${IMAGE_TAG} ."
        } 
      } 
    }

    stage('Push to Registry') { 
      steps { 
        withCredentials([usernamePassword(credentialsId:'docker_registry', usernameVariable:'REG_USER', passwordVariable:'REG_PASS')]) { 
          sh '''
            echo \$REG_PASS | docker login registry.local:5000 -u \$REG_USER --password-stdin
            docker push ${IMAGE_TAG}
            docker logout registry.local:5000 || true
          ''' 
        } 
      } 
    }

    stage('Deploy -> DEV') { 
      steps { 
        withCredentials([sshUserPrivateKey(credentialsId:'ansible_ssh', keyFileVariable:'SSH_KEY', usernameVariable:'SSH_USER')]) { 
          sh """
            mkdir -p .ssh && echo "\$(<\$SSH_KEY)" > .ssh/id_rsa && chmod 600 .ssh/id_rsa
            export ANSIBLE_HOST_KEY_CHECKING=False
            ansible-playbook -i ansible/inventory.ini ansible/deploy.yml --extra-vars "version=${params.VERSION}" --limit dev -u root --private-key=.ssh/id_rsa
          """ 
        } 
      } 
    }

    stage('Verify -> DEV') { 
      steps { 
        script {
          sh """
            curl -s http://127.0.0.1:$FLASK_PORT/health | python3 -c 'import sys, json; data=json.load(sys.stdin); sys.exit(0 if data.get("status") is True else 1)'
          """
          echo "DEV health check passed"
        }
      } 
    }

    stage('Promote to QUALIF') { 
      when { expression { return params.AUTO_PROMOTE } } 
      steps { 
        withCredentials([sshUserPrivateKey(credentialsId:'ansible_ssh', keyFileVariable:'SSH_KEY', usernameVariable:'SSH_USER')]) { 
          sh """
            export ANSIBLE_HOST_KEY_CHECKING=False
            ansible-playbook -i ansible/inventory.ini ansible/deploy.yml --extra-vars "version=${params.VERSION}" --limit qualif -u root --private-key="\$SSH_KEY"
          """ 
        } 
      } 
    }

    stage('Promote to PROD (Manual)') { 
      when { expression { return !params.AUTO_PROMOTE } } 
      steps { input message: "Valider déploiement en PROD ?" } 
    }

    stage('Deploy -> PROD') { 
      steps { 
        withCredentials([sshUserPrivateKey(credentialsId:'ansible_ssh', keyFileVariable:'SSH_KEY', usernameVariable:'SSH_USER')]) { 
          sh """
            export ANSIBLE_HOST_KEY_CHECKING=False
            ansible-playbook -i ansible/inventory.ini ansible/deploy.yml --extra-vars "version=${params.VERSION}" --limit prod -u root --private-key=.ssh/id_rsa
          """ 
        } 
      } 
    }

    stage('Verify -> PROD') { 
      steps { 
        script {
          sh """
            curl -s http://127.0.0.1:$FLASK_PORT/health | python3 -c 'import sys, json; data=json.load(sys.stdin); sys.exit(0 if data.get("status") is True else 1)'
          """
          echo "PROD health check passed"
        }
      } 
    }
  }
  post { 
    success { echo "Pipeline terminé : ${IMAGE_TAG}" } 
    failure { echo "Échec du pipeline — analyser logs. Eventuellement rollback." } 
    always { sh 'docker image prune -f || true' } 
  }
}

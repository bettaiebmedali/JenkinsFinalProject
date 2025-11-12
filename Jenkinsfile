pipeline {
  agent any
  environment {
    REGISTRY = "registry.local:5000"
    IMAGE = "myapp"
    SONAR_HOST = "http://localhost:9000"
  }
  parameters {
    string(name: 'VERSION', defaultValue: "0.1.0-${env.BUILD_NUMBER}", description: 'Tag image')
    booleanParam(name: 'AUTO_PROMOTE', defaultValue: false, description: 'Promote automatically to qualif/prod')
  }
  stages {
    stage('Checkout') { steps { checkout scm } }
    stage('Unit Tests') { steps { sh '''
      python3 -m pip install -r requirements.txt
      pytest -q || true
    ''' } }
    stage('SonarQube Analysis') { steps { withCredentials([string(credentialsId:'sonar_token', variable:'SONAR_TOKEN')]) { sh '''
      if command -v sonar-scanner >/dev/null 2>&1; then
        sonar-scanner -Dsonar.projectKey=my-app -Dsonar.host.url=${SONAR_HOST} -Dsonar.login=$SONAR_TOKEN
      else
        docker run --rm -v "${PWD}":/usr/src sonarsource/sonar-scanner-cli \
          -Dsonar.projectKey=my-app -Dsonar.sources=/usr/src -Dsonar.host.url=${SONAR_HOST} -Dsonar.login=$SONAR_TOKEN
      fi
    ''' } } }
    stage('Quality Gate') { steps { script { withCredentials([string(credentialsId:'sonar_token', variable:'SONAR_TOKEN')]) { def status = sh(returnStdout:true, script: """
      sleep 3
      curl -s -u $SONAR_TOKEN: ${SONAR_HOST}/api/qualitygates/project_status?projectKey=my-app | jq -r .projectStatus.status
    """).trim()
      echo "Sonar Quality Gate: ${status}"
      if (status != 'OK') { error("Quality Gate failed: ${status}") }
    } } } }
    stage('Build Docker Image') { steps { script { IMAGE_TAG = "${env.REGISTRY}/${env.IMAGE}:${params.VERSION}"; sh "docker build -t ${IMAGE_TAG} ." } } }
    stage('Push to Registry') { steps { withCredentials([usernamePassword(credentialsId:'docker_registry', usernameVariable:'REG_USER', passwordVariable:'REG_PASS')]) { sh '''
      echo $REG_PASS | docker login registry.local:5000 -u $REG_USER --password-stdin
      docker push ${IMAGE_TAG}
      docker logout registry.local:5000 || true
    ''' } } }
    stage('Deploy -> DEV') { steps { withCredentials([sshUserPrivateKey(credentialsId:'ansible_ssh', keyFileVariable:'SSH_KEY', usernameVariable:'SSH_USER')]) { sh """
      mkdir -p .ssh && echo "$(<$SSH_KEY)" > .ssh/id_rsa && chmod 600 .ssh/id_rsa
      export ANSIBLE_HOST_KEY_CHECKING=False
      ansible-playbook -i ansible/inventory.ini ansible/deploy.yml --extra-vars "version=${params.VERSION}" --limit dev -u root --private-key=.ssh/id_rsa
    """ } } }
    stage('Verify -> DEV') { steps { sh 'curl -fsS http://127.0.0.1:8080/health || (echo "DEV health failed" && exit 1)' } }
    stage('Promote to QUALIF') { when { expression { return params.AUTO_PROMOTE } } steps { withCredentials([sshUserPrivateKey(credentialsId:'ansible_ssh', keyFileVariable:'SSH_KEY', usernameVariable:'SSH_USER')]) { sh """
      export ANSIBLE_HOST_KEY_CHECKING=False
      ansible-playbook -i ansible/inventory.ini ansible/deploy.yml --extra-vars "version=${params.VERSION}" --limit qualif -u root --private-key=$SSH_KEY
    """ } } }
    stage('Promote to PROD (Manual)') { when { expression { return !params.AUTO_PROMOTE } } steps { input message: "Valider déploiement en PROD ?" } }
    stage('Deploy -> PROD') { steps { withCredentials([sshUserPrivateKey(credentialsId:'ansible_ssh', keyFileVariable:'SSH_KEY', usernameVariable:'SSH_USER')]) { sh """
      export ANSIBLE_HOST_KEY_CHECKING=False
      ansible-playbook -i ansible/inventory.ini ansible/deploy.yml --extra-vars "version=${params.VERSION}" --limit prod -u root --private-key=.ssh/id_rsa
    """ } } }
    stage('Verify -> PROD') { steps { sh 'curl -fsS http://127.0.0.1:8080/health || (echo "PROD health failed" && exit 1)' } }
  }
  post { success { echo "Pipeline terminé : ${IMAGE_TAG}" } failure { echo "Échec du pipeline — analyser logs. Eventuellement rollback." } always { sh 'docker image prune -f || true' } }
}
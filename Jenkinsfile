pipeline {
    agent any

    stages {
        

        
        stage('SonarQube Code Analysis') {
            steps {
                dir("${WORKSPACE}"){
                script {
                    def scannerHome = tool name: 'sonarqube', type: 'hudson.plugins.sonar.SonarRunnerInstallation'
                    withSonarQubeEnv('sonarqube') {
                        sh "${scannerHome}/bin/sonar-scanner \
                            -D sonar.projectVersion=1.0-SNAPSHOT \
                            -D sonar.qualityProfile=qp-1 \
                            -D sonar.projectBaseDir=/var/lib/jenkins/workspace/Snyk-Testing/snyk-code-container-scan/appcode \
                            -D sonar.projectKey=cas-prod-env \
                            -D sonar.sourceEncoding=UTF-8 \
                            -D sonar.language=python \
                            -D sonar.host.url=https://sonarqube-dev.connectandsell.com"
                    }
                }
            }
            }
       }
       stage("SonarQube Quality Gate Check") {
            steps {
                script {
                def qualityGate = waitForQualityGate()
                    
                    if (qualityGate.status != 'OK') {
                        echo "${qualityGate.status}"
                        error "Quality Gate failed: ${qualityGateStatus}"
                    }
                    else {
                        echo "${qualityGate.status}"
                        echo "SonarQube Quality Gates Passed"
                    }
                }
            }
        }
        stage('Run main.py') {
            steps {
                // Run the Python script
                bat 'python main.py'
            }
        }
    }

}

pipeline {
    agent any

    tools {
        // Define SonarQube Scanner tool if it's configured in Jenkins' global tool configuration
        sonarScanner 'sonar-scanner' // The name provided in Global Tool Configuration
    }

    stages {
        stage('SonarQube Code Analysis') {
            steps {
                script {
                    // Fetch the SonarQube Scanner home directory
                    def scannerHome = tool name: 'sonar-scanner', type: 'hudson.plugins.sonar.SonarRunnerInstallation'

                    // Run SonarQube Scanner
                    withSonarQubeEnv('sonarqube') { // Ensure 'sonarqube' is the name used in SonarQube Servers configuration
                        sh """
                            ${scannerHome}/bin/sonar-scanner \
                            -Dsonar.projectKey=cas-prod-env \
                            -Dsonar.sources=. \
                            -Dsonar.host.url=https://sonarqube-dev.connectandsell.com \
                            -Dsonar.login=squ_e67e26dd043974e7a23f2da0f5490fbfc8cc9bf2
                        """
                    }
                }
            }
        }

        stage('SonarQube Quality Gate Check') {
            steps {
                script {
                    // Wait for the quality gate status to be available
                    def qualityGate = waitForQualityGate()
                    
                    // Check the quality gate status and fail the build if the status is not 'OK'
                    if (qualityGate.status != 'OK') {
                        error "Quality Gate failed: ${qualityGate.status}"
                    }
                }
            }
        }
    }

   
}

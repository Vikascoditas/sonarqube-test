pipeline {
    agent any

    stages {
        stage('SonarQube Code Analysis') {
            steps {
                dir("${WORKSPACE}") {
                    script {
                        def scannerHome = tool name: 'sonarqube', type: 'hudson.plugins.sonar.SonarRunnerInstallation'
                        withSonarQubeEnv('sonarqube') {
                            sh """
                                ${scannerHome}/bin/sonar-scanner \
                                -Dsonar.projectKey=cas-prod-env \
                                -Dsonar.sources=. \
                                -Dsonar.host.url=https://sonarqube-dev.connectandsell.com \
                                -Dsonar.login=${env.SONARQUBE_TOKEN}
                            """
                        }
                    }
                }
            }
        }

        stage('SonarQube Quality Gate Check') {
            steps {
                script {
                    // Wait for the quality gate status to be available
                    def qualityGate = waitForQualityGate()
                    
                    // Check the quality gate status and fail the build if not 'OK'
                    if (qualityGate.status != 'OK') {
                        error "Quality Gate failed: ${qualityGate.status}"
                    }
                }
            }
        }
    }
}

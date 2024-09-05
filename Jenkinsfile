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
                                -Dsonar.token=squ_e67e26dd043974e7a23f2da0f5490fbfc8cc9bf2
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

        stage('Install Python Dependencies') {
            steps {
                dir("${WORKSPACE}") {
                    script {
                        // Ensure pip is up-to-date
                        sh 'python3 -m pip install --upgrade pip'
                        
                        // Install dependencies from requirements.txt
                        sh 'pip3 install -r requirements.txt'
                    }
                }
            }
        }

        stage('Run Python Script') {
            steps {
                dir("${WORKSPACE}") {
                    script {
                        sh 'python3 main.py'
                    }
                }
            }
        }
    }
}

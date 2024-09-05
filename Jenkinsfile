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

        stage('Fetch SonarQube Report') {
            steps {
                script {
                    // Define SonarQube URL and API token
                    def sonarHost = 'https://sonarqube-dev.connectandsell.com'
                    def sonarToken = 'squ_e67e26dd043974e7a23f2da0f5490fbfc8cc9bf2'
                    def taskId = env.SONARQUBE_TASK_ID
                    def apiUrl = "${sonarHost}/api/ce/task?id=${taskId}"
                    
                    // Fetch the SonarQube task report
                    def response = sh(script: "curl -u ${sonarToken}: ${apiUrl}", returnStdout: true).trim()
                    
                    // Parse the response and print summary
                    def report = readJSON text: response
                    echo "SonarQube Report Summary:"
                    echo "Status: ${report.task.status}"
                    echo "Warnings: ${report.task.warningCount}"
                    echo "Execution Time: ${report.task.executionTimeMs} ms"
                    echo "Warnings Details: ${report.task.warnings}"
                }
            }
        }
    }

    post {
        always {
            echo 'Cleaning up...'
            // Perform any cleanup actions here
        }
        success {
            echo 'Pipeline completed successfully!'
        }
        failure {
            echo 'Pipeline failed.'
        }
    }
}

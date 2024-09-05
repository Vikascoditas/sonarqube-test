pipeline {
    agent any

    stages {
        stage('Install Python Dependencies') {
            steps {
                sh 'pip3 install -r requirements.txt'
            }
        }

        stage('Run Tests with Coverage') {
            steps {
                // Run pytest with coverage and generate an XML report
                sh 'pytest --cov=common --cov=dbConfig --cov=self_jobs --cov-report=xml'
            }
        }

        stage('SonarQube Code Analysis') {
            steps {
                script {
                    def scannerHome = tool name: 'sonarqube', type: 'hudson.plugins.sonar.SonarRunnerInstallation'
                    withSonarQubeEnv('sonarqube') {
                        // Run the SonarQube scanner, ensuring the correct path to the coverage report
                        sh """
                            ${scannerHome}/bin/sonar-scanner \
                            -Dsonar.projectKey=cas-prod-env \
                            -Dsonar.sources=. \
                            -Dsonar.python.coverage.reportPaths=coverage.xml \
                            -Dsonar.host.url=https://sonarqube-dev.connectandsell.com \
                            -Dsonar.token=squ_e67e26dd043974e7a23f2da0f5490fbfc8cc9bf2
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
                    if (qualityGate.status != 'OK') {
                        error "Quality Gate failed: ${qualityGate.status}"
                    }
                }
            }
        }

        stage('Fetch SonarQube Report') {
            steps {
                script {
                    // Define SonarQube API details
                    def sonarHost = 'https://sonarqube-dev.connectandsell.com'
                    def sonarToken = 'squ_e67e26dd043974e7a23f2da0f5490fbfc8cc9bf2'
                    // Assuming that SONARQUBE_TASK_ID is set by the SonarQube plugin
                    def taskId = env.SONARQUBE_TASK_ID
                    if (taskId == null) {
                        error "SONARQUBE_TASK_ID is not available"
                    }
                    def apiUrl = "${sonarHost}/api/ce/task?id=${taskId}"

                    // Fetch the SonarQube task report
                    def response = sh(script: "curl -u ${sonarToken}: ${apiUrl}", returnStdout: true).trim()

                    // Parse the response and print the report summary
                    def report = readJSON text: response
                    echo "SonarQube Report Summary:"
                    echo "Status: ${report.task.status}"
                    echo "Warnings: ${report.task.warningCount ?: 'None'}"
                    echo "Execution Time: ${report.task.executionTimeMs} ms"
                    echo "Warnings Details: ${report.task.warnings ?: 'No warnings'}"
                }
            }
        }
    }

    post {
        always {
            echo 'Cleaning up...'
        }
        success {
            echo 'Pipeline completed successfully!'
        }
        failure {
            echo 'Pipeline failed.'
        }
    }
}

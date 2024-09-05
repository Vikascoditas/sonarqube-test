pipeline {
    agent any

    stages {
        stage('Install Python Dependencies') {
            steps {
                dir("${WORKSPACE}") {
                    script {
                        sh 'pip3 install --upgrade pip'
                        sh 'pip3 install -r requirements.txt'
                    }
                }
            }
        }

        stage('Run Tests') {
            steps {
                dir("${WORKSPACE}") {
                    script {
                        // Run tests and generate coverage report
                        sh 'pytest --cov=common --cov=dbconfig --cov=self_jobs --cov-report=xml'
                    }
                }
            }
        }

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
                                -Dsonar.token=squ_e67e26dd043974e7a23f2da0f5490fbfc8cc9bf2 \
                                -Dsonar.python.coverage.reportPaths=coverage.xml
                            """
                        }
                    }
                }
            }
        }

        stage('SonarQube Quality Gate Check') {
            steps {
                script {
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
                    def sonarHost = 'https://sonarqube-dev.connectandsell.com'
                    def sonarToken = 'squ_e67e26dd043974e7a23f2da0f5490fbfc8cc9bf2'
                    def taskId = env.SONARQUBE_TASK_ID
                    def apiUrl = "${sonarHost}/api/ce/task?id=${taskId}"
                    def response = sh(script: "curl -u ${sonarToken}: ${apiUrl}", returnStdout: true).trim()
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
        }
        success {
            echo 'Pipeline completed successfully!'
        }
        failure {
            echo 'Pipeline failed.'
        }
    }
}

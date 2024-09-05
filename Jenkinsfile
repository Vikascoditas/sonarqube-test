pipeline {
    agent any

    environment {
        SONARQUBE_URL = 'https://sonarqube-dev.connectandsell.com'
        SONARQUBE_TOKEN = credentials('sonarqube') // Use Jenkins credentials plugin to manage tokens
    }

    parameters {
        string(name: 'SONARQUBE_TASK_ID', defaultValue: '', description: 'SonarQube task ID for checking status')
    }

    stages {
        stage('Checkout') {
            steps {
                // Checkout code from repository
                checkout scm
            }
        }

        stage('Build') {
            steps {
                // Build your project if necessary
                echo 'Building the project...'
                // For example: sh 'mvn clean package'
            }
        }

        stage('SonarQube Analysis') {
            steps {
                script {
                    // Run SonarQube analysis
                    sh 'mvn sonar:sonar -Dsonar.projectKey=cas-prod-env -Dsonar.host.url=${SONARQUBE_URL} -Dsonar.login=${SONARQUBE_TOKEN}'
                }
            }
        }

        stage('Check Quality Gate') {
            steps {
                script {
                    // Check the quality gate status
                    def statusResponse = sh(script: "curl -u ${SONARQUBE_TOKEN}: ${SONARQUBE_URL}/api/qualitygates/project_status?projectKey=my_project", returnStdout: true).trim()
                    echo "Quality Gate Status: ${statusResponse}"
                    
                    def jsonResponse = readJSON(text: statusResponse)
                    def status = jsonResponse.projectStatus.status
                    if (status != 'OK') {
                        error "SonarQube Quality Gate failed. Status: ${status}"
                    }
                }
            }
        }

        stage('Run Python Script') {
            steps {
                script {
                    // Run your Python script
                    sh 'python3 main.py'
                }
            }
        }

        stage('Post-Processing') {
            steps {
                echo 'Post-processing...'
                // Additional steps like cleanup or notifications
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

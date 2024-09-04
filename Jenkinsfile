pipeline {
    agent any

    stages {
        stage('Setup Environment') {
            steps {
                // Ensures that Python is available
                bat 'python --version'
            }
        }

        stage('Run main.py') {
            steps {
                // Run the Python script
                bat 'python main.py'
            }
        }
    }

    post {
        always {
            // Print the current workspace directory
            echo "Current Workspace: ${env.WORKSPACE}"

            // Clean up the workspace after the build
            cleanWs()
        }
    }
}

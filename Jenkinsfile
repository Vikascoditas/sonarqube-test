pipeline {
    agent { label 'windows_slave' }
    environment {
        GITHUB_REPO = "git@github.com:ConnectAndSell/CAS-Infrastructure.git"
        WORKSPACE = "${env.WORKSPACE}"
        PYTHON_PATH = "C:\\Users\\Administrator\\AppData\\Local\\Programs\\Python\\Python312\\python.exe"
    }
    stages {
        stage('Git checkout') {
            steps {
                git(
                    credentialsId: '60dabad4-fa48-49e6-92c3-a07403777ea1',
                    url: "${GITHUB_REPO}",
                    branch: 'sonarqube'
                )
            }
        }
        stage('Set GCP Project') {
            steps {
                script {
                    bat "gcloud config set project cas-prod-env"
                }
            }
        }
        stage('SonarQube Code Analysis') {
            steps {
                dir("${WORKSPACE}"){
                script {
                    def scannerHome = tool name: 'scanner-name', type: 'hudson.plugins.sonar.SonarRunnerInstallation'
                    withSonarQubeEnv('sonar') {
                        sh "echo $pwd"
                        sh "${scannerHome}/bin/sonar-scanner"
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
        stage('Execute Script') {
            steps {
                script {
                    dir(WORKSPACE) {
                        
                        bat "${PYTHON_PATH} main.py"
                    }
                }
            }
        }
    }
}

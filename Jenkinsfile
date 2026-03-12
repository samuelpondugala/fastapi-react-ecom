pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
    }

    environment {
        PYTHONUNBUFFERED = '1'
        PIP_DISABLE_PIP_VERSION_CHECK = '1'
        CI = 'true'
    }

    stages {
        stage('Check Tools') {
            steps {
                sh '''
                    python3 --version
                    node --version
                    npm --version
                '''
            }
        }

        stage('Backend Test') {
            steps {
                dir('fastapi') {
                    sh '''
                        export APP_ENV=test
                        export DEBUG=false
                        export JWT_SECRET_KEY=test-secret-key
                        python3 -m venv .venv
                        . .venv/bin/activate
                        pip install --upgrade pip
                        pip install -r requirements-dev.txt
                        mkdir -p ../reports
                        pytest --junitxml=../reports/backend-pytest.xml
                    '''
                }
            }
        }

        stage('Frontend Build') {
            steps {
                dir('react') {
                    sh '''
                        npm ci
                        npm run build
                    '''
                }
            }
        }
    }

    post {
        always {
            junit allowEmptyResults: true, testResults: 'reports/backend-pytest.xml'
            archiveArtifacts allowEmptyArchive: true, artifacts: 'react/dist/**'
        }
    }
}

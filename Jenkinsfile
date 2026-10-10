// ══════════════════════════════════════════════════════════════════
// Jenkinsfile — Healthcare Claim Finalization Agent
// CI/CD pipeline: build → test → scan → push image → deploy to OpenShift
// ══════════════════════════════════════════════════════════════════

pipeline {

    // Run on any available agent (label can be tightened to a specific node)
    agent { label 'docker' }

    // ── Pipeline-level environment ──────────────────────────────────
    environment {
        APP_NAME        = "claim-finalization-agent"
        IMAGE_REPO      = "registry.example.com/healthcare"
        IMAGE_TAG       = "${env.BUILD_NUMBER}-${env.GIT_COMMIT[0..6]}"
        FULL_IMAGE      = "${IMAGE_REPO}/${APP_NAME}:${IMAGE_TAG}"
        LATEST_IMAGE    = "${IMAGE_REPO}/${APP_NAME}:latest"

        OCP_PROJECT     = "healthcare-prod"
        OCP_API_URL     = "https://api.ocp.example.com:6443"
        DEPLOYMENT_NAME = "claim-finalization-agent"

        SONAR_PROJECT   = "healthcare-claim-agent"
        PYTHON_VERSION  = "3.12"
    }

    // ── Build options ───────────────────────────────────────────────
    options {
        buildDiscarder(logRotator(numToKeepStr: '10'))
        timeout(time: 45, unit: 'MINUTES')
        timestamps()
        disableConcurrentBuilds()
    }

    // ── Trigger: run on every push; nightly at 2 AM ─────────────────
    triggers {
        githubPush()
        cron('H 2 * * *')
    }

    // ════════════════════════════════════════════════════════════════
    // STAGES
    // ════════════════════════════════════════════════════════════════
    stages {

        // ── 1. Checkout ─────────────────────────────────────────────
        stage('Checkout') {
            steps {
                checkout scm
                sh 'git log -1 --oneline'
            }
        }

        // ── 2. Setup Python virtualenv ──────────────────────────────
        stage('Setup Environment') {
            steps {
                sh """
                    python${PYTHON_VERSION} -m venv .venv
                    . .venv/bin/activate
                    pip install --upgrade pip
                    pip install -r healthcare-claim-agent/requirements.txt
                    pip install pytest pytest-cov flake8 bandit safety
                """
            }
        }

        // ── 3. Lint ─────────────────────────────────────────────────
        stage('Lint (flake8)') {
            steps {
                sh """
                    . .venv/bin/activate
                    flake8 healthcare-claim-agent/agents/ \
                        --max-line-length=120 \
                        --exclude=__pycache__ \
                        --format=pylint \
                        --output-file=flake8-report.txt || true
                """
            }
            post {
                always {
                    archiveArtifacts artifacts: 'flake8-report.txt', allowEmptyArchive: true
                }
            }
        }

        // ── 4. Unit Tests ───────────────────────────────────────────
        stage('Unit Tests') {
            steps {
                sh """
                    . .venv/bin/activate
                    cd healthcare-claim-agent
                    pytest tests/ \
                        -v \
                        --cov=agents \
                        --cov-report=xml:coverage.xml \
                        --cov-report=html:coverage-html \
                        --junitxml=test-results.xml
                """
            }
            post {
                always {
                    junit 'healthcare-claim-agent/test-results.xml'
                    publishHTML([
                        allowMissing: false,
                        alwaysLinkToLastBuild: true,
                        keepAll: true,
                        reportDir: 'healthcare-claim-agent/coverage-html',
                        reportFiles: 'index.html',
                        reportName: 'Coverage Report'
                    ])
                    // Enforce minimum 80% coverage
                    sh """
                        . .venv/bin/activate
                        coverage report --fail-under=80
                    """
                }
            }
        }

        // ── 5. Security Scan (Bandit + Safety) ──────────────────────
        stage('Security Scan') {
            parallel {
                stage('SAST — Bandit') {
                    steps {
                        sh """
                            . .venv/bin/activate
                            bandit -r healthcare-claim-agent/agents/ \
                                -f json \
                                -o bandit-report.json \
                                --exit-zero
                        """
                    }
                    post {
                        always { archiveArtifacts artifacts: 'bandit-report.json' }
                    }
                }
                stage('Dependency CVE — Safety') {
                    steps {
                        sh """
                            . .venv/bin/activate
                            safety check \
                                -r healthcare-claim-agent/requirements.txt \
                                --json > safety-report.json || true
                        """
                    }
                    post {
                        always { archiveArtifacts artifacts: 'safety-report.json' }
                    }
                }
            }
        }

        // ── 6. SonarQube Analysis ────────────────────────────────────
        stage('SonarQube Analysis') {
            environment {
                SONAR_TOKEN = credentials('sonarqube-token')
            }
            steps {
                withSonarQubeEnv('SonarQube') {
                    sh """
                        sonar-scanner \
                            -Dsonar.projectKey=${SONAR_PROJECT} \
                            -Dsonar.sources=healthcare-claim-agent/agents \
                            -Dsonar.tests=healthcare-claim-agent/tests \
                            -Dsonar.python.coverage.reportPaths=healthcare-claim-agent/coverage.xml \
                            -Dsonar.python.bandit.reportPaths=bandit-report.json
                    """
                }
            }
        }

        // ── 7. Quality Gate ──────────────────────────────────────────
        stage('Quality Gate') {
            steps {
                timeout(time: 10, unit: 'MINUTES') {
                    waitForQualityGate abortPipeline: true
                }
            }
        }

        // ── 8. Build Docker Image ────────────────────────────────────
        stage('Build Image') {
            steps {
                dir('healthcare-claim-agent') {
                    sh """
                        docker build \
                            --build-arg BUILD_DATE=\$(date -u +%Y-%m-%dT%H:%M:%SZ) \
                            --build-arg GIT_COMMIT=${env.GIT_COMMIT} \
                            --label "app=${APP_NAME}" \
                            --label "version=${IMAGE_TAG}" \
                            -t ${FULL_IMAGE} \
                            -t ${LATEST_IMAGE} \
                            .
                    """
                }
            }
        }

        // ── 9. Container Image Scan (Trivy) ──────────────────────────
        stage('Image Scan (Trivy)') {
            steps {
                sh """
                    trivy image \
                        --exit-code 0 \
                        --severity HIGH,CRITICAL \
                        --format json \
                        --output trivy-report.json \
                        ${FULL_IMAGE}
                """
            }
            post {
                always { archiveArtifacts artifacts: 'trivy-report.json' }
            }
        }

        // ── 10. Push Image to Registry ───────────────────────────────
        stage('Push Image') {
            when {
                anyOf {
                    branch 'main'
                    branch 'release/*'
                }
            }
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'registry-credentials',
                    usernameVariable: 'REGISTRY_USER',
                    passwordVariable: 'REGISTRY_PASS'
                )]) {
                    sh """
                        docker login ${IMAGE_REPO} \
                            -u ${REGISTRY_USER} \
                            -p ${REGISTRY_PASS}
                        docker push ${FULL_IMAGE}
                        docker push ${LATEST_IMAGE}
                    """
                }
            }
        }

        // ── 11. Deploy to OpenShift ───────────────────────────────────
        stage('Deploy to OpenShift') {
            when { branch 'main' }
            environment {
                OCP_TOKEN = credentials('openshift-sa-token')
            }
            steps {
                sh """
                    # Login to OpenShift cluster
                    oc login ${OCP_API_URL} \
                        --token=${OCP_TOKEN} \
                        --insecure-skip-tls-verify=false

                    # Switch to target project
                    oc project ${OCP_PROJECT}

                    # Apply manifests (idempotent)
                    oc apply -f healthcare-claim-agent/openshift/

                    # Update the deployment image to the newly built tag
                    oc set image deployment/${DEPLOYMENT_NAME} \
                        ${APP_NAME}=${FULL_IMAGE} \
                        --record

                    # Wait for rollout to complete (5-minute timeout)
                    oc rollout status deployment/${DEPLOYMENT_NAME} \
                        --timeout=5m

                    # Verify pods are running
                    oc get pods -l app=${APP_NAME}
                """
            }
        }

        // ── 12. Smoke Test (post-deploy) ─────────────────────────────
        stage('Smoke Test') {
            when { branch 'main' }
            steps {
                sh """
                    APP_URL=\$(oc get route ${APP_NAME} \
                        -n ${OCP_PROJECT} \
                        -o jsonpath='{.spec.host}')

                    echo "Running smoke test against https://\${APP_URL}"

                    # Health check
                    curl -sf https://\${APP_URL}/health | grep '"status":"ok"'

                    # Functional smoke: submit a test claim
                    STATUS=\$(curl -sf -X POST https://\${APP_URL}/claims/process \
                        -H 'Content-Type: application/json' \
                        -d '{
                            "claim_id": "SMOKE-001",
                            "member_id": "M001",
                            "provider_npi": "1234567890",
                            "service_date": "2024-01-01",
                            "diagnosis_codes": ["I10"],
                            "procedure_codes": ["99214"],
                            "billed_amount": 210.0
                        }' | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])")

                    echo "Smoke test claim status: \${STATUS}"
                    [ "\${STATUS}" = "FINALIZED" ] || (echo "Smoke test FAILED" && exit 1)
                """
            }
        }

    } // end stages

    // ════════════════════════════════════════════════════════════════
    // POST actions
    // ════════════════════════════════════════════════════════════════
    post {
        success {
            slackSend(
                channel: '#claim-agent-deployments',
                color: 'good',
                message: "✅ *${APP_NAME}* build #${BUILD_NUMBER} deployed successfully to *${OCP_PROJECT}*\nImage: `${FULL_IMAGE}`\n${BUILD_URL}"
            )
        }
        failure {
            slackSend(
                channel: '#claim-agent-deployments',
                color: 'danger',
                message: "❌ *${APP_NAME}* build #${BUILD_NUMBER} FAILED at stage: ${env.STAGE_NAME}\n${BUILD_URL}"
            )
            emailext(
                to: 'platform-team@example.com',
                subject: "[FAILED] ${APP_NAME} Build #${BUILD_NUMBER}",
                body: "Pipeline failed at stage: ${env.STAGE_NAME}\nSee: ${BUILD_URL}"
            )
        }
        always {
            // Clean Docker images to save disk space
            sh "docker rmi ${FULL_IMAGE} ${LATEST_IMAGE} || true"
            cleanWs()
        }
    }

} // end pipeline

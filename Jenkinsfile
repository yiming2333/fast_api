// =====================================================================
// FastAPI 示例项目 Jenkins Pipeline
// 功能：lint -> 依赖安装 -> 单元测试 -> Docker 镜像构建 -> 推送 -> 部署
// 使用声明式 pipeline，便于在 Jenkins "Blue Ocean" 中可视化。
// 前置条件（Jenkins 管理员一次性配置）：
//   1. 安装插件：Pipeline、Docker Pipeline、Stage View
//   2. 配置凭据：
//      - 'docker-registry'    类型 Username/Password，用于推送镜像
//      - 'github-creds'       可选，用于私有仓库拉取
//   3. Jenkins agent 已安装 docker，且 jenkins 用户在 docker 组中
// =====================================================================
pipeline {
    agent any

    options {
        timestamps()              // 日志带时间戳
        timeout(time: 30, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '20'))  // 只保留最近 20 次构建
        disableConcurrentBuilds()  // 同一分支串行构建，避免镜像 tag 冲突
    }

    environment {
        // 镜像 tag：分支名-构建号-前 8 位 commit，便于回溯
        IMAGE_TAG        = "${env.BRANCH_NAME ?: 'main'}-${env.BUILD_NUMBER}-${sh(script: 'git rev-parse --short=8 HEAD', returnStdout: true).trim()}"
        IMAGE_NAME       = "fast_api"
        REGISTRY         = "registry.example.com"  // 改为你的私有仓库
        DOCKER_IMAGE     = "${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"
        // 从凭据中读取 docker registry 用户名密码
        DOCKER_CREDENTIALS = credentials('docker-registry')
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
                echo "构建分支: ${env.BRANCH_NAME ?: 'main'}，镜像 tag: ${IMAGE_TAG}"
            }
        }

        stage('Lint') {
            // 静态检查：语法错误、未使用导入等。失败则中止流水线。
            steps {
                sh '''
                    python -m pip install --quiet ruff || true
                    # --exit-zero 让 ruff 不因风格问题阻断，仅用于报告
                    ruff check app/ tests/ --exit-zero || true
                '''
            }
        }

        stage('Test') {
            // 在 Docker 内运行测试，环境与生产完全一致
            steps {
                sh 'docker compose --profile test run --rm test'
            }
            post {
                always {
                    junit allowEmptyResults: true, testResults: 'test-reports/*.xml'
                }
            }
        }

        stage('Build Image') {
            steps {
                sh "docker build -t ${DOCKER_IMAGE} ."
            }
        }

        stage('Push Image') {
            when {
                // 仅在 main / release 分支推送镜像，避免 PR 污染仓库
                anyOf {
                    branch 'main'
                    branch 'release/*'
                }
            }
            steps {
                sh "echo ${DOCKER_CREDENTIALS_PSW} | docker login ${REGISTRY} -u ${DOCKER_CREDENTIALS_USR} --password-stdin"
                sh "docker push ${DOCKER_IMAGE}"
                // 同时打 latest tag，方便运维拉最新稳定版
                sh "docker tag ${DOCKER_IMAGE} ${REGISTRY}/${IMAGE_NAME}:latest"
                sh "docker push ${REGISTRY}/${IMAGE_NAME}:latest"
            }
            post {
                always {
                    sh "docker logout ${REGISTRY} || true"
                }
            }
        }

        stage('Deploy') {
            when {
                branch 'main'
            }
            // 真实部署应在远程主机执行：docker pull ... && docker compose up -d
            steps {
                echo "部署 ${DOCKER_IMAGE}（此处仅占位，请按实际环境替换为 SSH / Ansible / kubectl）"
            }
        }
    }

    post {
        success {
            echo "Pipeline 成功: ${DOCKER_IMAGE}"
        }
        failure {
            echo "Pipeline 失败，请检查上方日志"
            // 可在此处接入钉钉/飞书/Slack 通知
        }
        cleanup {
            // 清理本机构建的镜像与悬空层，避免磁盘膨胀
            sh "docker rmi ${DOCKER_IMAGE} || true"
            sh "docker image prune -f || true"
        }
    }
}

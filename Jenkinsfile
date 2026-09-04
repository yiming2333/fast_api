import groovy.json.JsonOutput

// ============================================================================
// 跨平台 Jenkinsfile：Jenkins + Docker 跑测试（容器内自带 Python + 依赖）
//
// 关键点：Jenkins 在 Windows 上通常以 LocalSystem 服务账户运行，
// 该账户的 PATH 默认不包含 Docker Desktop 的 bin 目录
// （Docker Desktop 默认装在 %LOCALAPPDATA%\Programs\DockerDesktop\resources\bin）。
// 通过在 environment 块显式把 docker 路径加进 PATH 解决。
// ============================================================================

pipeline {
    agent any

    options {
        timeout(time: 30, unit: 'MINUTES')
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '30'))
    }

    parameters {
        choice(name: 'PARALLEL',       choices: ['off', 'auto', '2', '3','4','5', '10'], description: '并发模式: off=串行, auto=自动, 数字=指定worker数')
        // 如果你需要 ENV 参数，可以取消下面这行的注释：
        // choice(name: 'ENV', choices: ['dev', 'prod'], description: '部署环境')
    }

    environment {
        // Docker Compose 项目名（避免与其它项目冲突）
        COMPOSE_PROJECT_NAME = 'fast_api'
        ALLURE_RESULTS       = 'allure-results'
        ALLURE_REPORT_NAME   = 'AllureReport'
        MAIL_RECIPIENT       = 'yiming_2333@sina.com'
        GIT_URL              = 'https://github.com/yiming2333/fast_api.git'
        GIT_BRANCH           = 'master'
        GIT_CREDENTIALS_ID   = ''
        REPORT_LINK          = "${env.JENKINS_URL}job/${env.JOB_NAME}/${env.BUILD_NUMBER}/allure/"
        DINGTALK_WEBHOOK     = credentials('dingtalk_webhook')
        DINGTALK_KEYWORD     = '测试'

        // ===== 关键：把 Docker Desktop 的 bin 目录加到 PATH =====
        // Docker Desktop 默认装在用户级目录，Jenkins 服务账户（LocalSystem）看不到。
        // 这里显式拼接，让 docker / docker-compose 命令在 Jenkins shell 里可用。
        // 如果 Docker Desktop 装在别处，改成对应路径即可。
        DOCKER_BIN           = 'C:\\Users\\27088\\AppData\\Local\\Programs\\DockerDesktop\\resources\\bin'
        PATH                 = "${env.DOCKER_BIN};${env.PATH}"
    }

    stages {
        stage('🧹 1. 准备 & 拉取代码') {
            stages {
                stage('1.0 👤 获取构建用户') {
                    steps {
                        script {
                            env.ENV = params.ENV ?: 'dev'
                            try {
                                wrap([$class: 'BuildUser']) {
                                    env.TRIGGER_USER = env.BUILD_USER_ID ?: 'unknown'
                                }
                            } catch (e) {
                                echo "无法获取构建用户: ${e.message}"
                                env.TRIGGER_USER = 'unknown'
                            }
                            echo "本次构建触发人: ${env.TRIGGER_USER}"
                            echo "当前环境: ${env.ENV}"
                        }
                    }
                }

                stage('1.1 Preflight 诊断') {
                    steps {
                        script {
                            echo "========== 环境诊断 =========="
                            echo "NODE_NAME: ${env.NODE_NAME}"
                            echo "WORKSPACE: ${env.WORKSPACE}"
                            echo "DOCKER_BIN: ${env.DOCKER_BIN}"
                        }
                        cmd(
                            sh  : '''
                                echo "PATH=$PATH"
                                which docker 2>/dev/null || true
                                docker --version 2>&1 || true
                                docker-compose version 2>&1 || true
                            ''',
                            bat : '''
                                chcp 65001 >nul
                                echo PATH=%PATH%
                                where docker
                                docker --version
                                docker-compose version
                            '''
                        )
                    }
                }

                stage('1.2 清理工作区') {
                    steps {
                        echo "清理旧报告、缓存..."
                        cmd(
                            sh  : '''
                                rm -rf allure-results allure-report logs __pycache__ .pytest_cache
                                echo "Workspace cleanup done"
                            ''',
                            bat : '''
                                chcp 65001 >nul
                                if exist allure-results rmdir /s /q allure-results
                                if exist allure-report rmdir /s /q allure-report
                                if exist logs rmdir /s /q logs
                                if exist __pycache__ rmdir /s /q __pycache__
                                if exist .pytest_cache rmdir /s /q .pytest_cache
                                echo Workspace cleanup done
                            '''
                        )
                    }
                }

                stage('1.3 拉取代码') {
                    options { retry(3) }
                    steps {
                        echo "正在从 Git 拉取代码 (${env.GIT_BRANCH})..."
                        script {
                            def gitConfig = [branch: env.GIT_BRANCH, url: env.GIT_URL]
                            if (env.GIT_CREDENTIALS_ID?.trim()) {
                                gitConfig.credentialsId = env.GIT_CREDENTIALS_ID
                            }
                            git gitConfig
                        }
                    }
                }
            }
        }

        stage('🐳 2. 构建 Docker 镜像') {
            steps {
                echo "构建 test 镜像（含运行时 + 测试依赖 + 测试代码）..."
                cmd(
                    sh  : "docker-compose -p ${env.COMPOSE_PROJECT_NAME} build test",
                    bat : "docker-compose -p ${env.COMPOSE_PROJECT_NAME} build test"
                )
            }
        }

        stage('🚀 3. 执行 fast_api 测试') {
            steps {
                script {
                    def xdistArg = ''
                    switch (params.PARALLEL) {
                        case 'off':  xdistArg = ''; break
                        case 'auto': xdistArg = '-n auto'; break
                        default:     xdistArg = "-n ${params.PARALLEL}"; break
                    }
                    // 容器内 pytest 输出 allure 结果到 /app/allure-results，
                    // 已通过 docker-compose.yml 挂载到宿主机 ./allure-results
                    def testCmd = "pytest ${xdistArg} -v --alluredir=/app/allure-results"
                    echo "执行测试命令 (容器内): ${testCmd}"

                    def baseUrl = getBaseUrl(env.ENV)
                    cmd(
                        sh  : """
                            BASE_URL=${baseUrl} \
                            docker-compose -p ${env.COMPOSE_PROJECT_NAME} run --rm test ${testCmd}
                        """,
                        bat : """
                            chcp 65001 >nul
                            set BASE_URL=${baseUrl}&& docker-compose -p ${env.COMPOSE_PROJECT_NAME} run --rm test ${testCmd}
                        """
                    )
                }
            }
        }

        stage('📝 4. 写入 Allure 元数据') {
            steps {
                script {
                    cmd(
                        sh  : "mkdir -p ${env.ALLURE_RESULTS}",
                        bat : "if not exist ${env.ALLURE_RESULTS} mkdir ${env.ALLURE_RESULTS}"
                    )

                    def envProps = """
                        Environment=${env.ENV}
                        Parallel.Mode=${params.PARALLEL}
                        Trigger.User=${env.TRIGGER_USER ?: 'unknown'}
                        Build.Number=${env.BUILD_NUMBER}
                        Git.Branch=${env.GIT_BRANCH}
                        Base.URL=${getBaseUrl(env.ENV)}
                        OS=Linux (Docker)
                    """.stripIndent().trim()
                    writeFile file: "${env.ALLURE_RESULTS}/environment.properties", text: envProps, encoding: 'UTF-8'

                    def executorData = [
                        name       : 'Jenkins',
                        type       : 'jenkins',
                        url        : env.JENKINS_URL,
                        buildOrder : env.BUILD_NUMBER.toInteger(),
                        buildName  : "#${env.BUILD_NUMBER}",
                        buildUrl   : "${env.JENKINS_URL}job/${env.JOB_NAME}/${env.BUILD_NUMBER}/",
                        reportUrl  : env.REPORT_LINK,
                        reportName : env.ALLURE_REPORT_NAME
                    ]
                    def jsonStr = JsonOutput.toJson(executorData)
                    writeFile file: "${env.ALLURE_RESULTS}/executor.json", text: jsonStr, encoding: 'UTF-8'
                    echo "Allure 元数据已写入"
                }
            }
        }

        stage('📊 5. 生成 Allure 报告') {
            steps {
                echo "正在生成 Allure 报告..."
                allure includeProperties: false,
                       jdk: '',
                       results: [[path: env.ALLURE_RESULTS]],
                       reportBuildPolicy: 'ALWAYS'
            }
        }
    }

    post {
        always {
            echo "========== 🧹 收尾清理 =========="
            script {
                // 关闭容器、清理卷，避免占用资源
                cmd(
                    sh  : "docker-compose -p ${env.COMPOSE_PROJECT_NAME} down -v",
                    bat : "docker-compose -p ${env.COMPOSE_PROJECT_NAME} down -v"
                )
                archiveArtifacts artifacts: 'logs/*.log', allowEmptyArchive: true
            }
        }

        failure {
            echo "存在失败的测试用例"
            script {
                catchError(buildResult: null, stageResult: null) {
                    cmd(
                        sh  : "docker-compose -p ${env.COMPOSE_PROJECT_NAME} logs --tail=200 > diagnostics.log",
                        bat : "docker-compose -p ${env.COMPOSE_PROJECT_NAME} logs --tail=200 > diagnostics.log"
                    )
                    archiveArtifacts artifacts: 'diagnostics.log', allowEmptyArchive: true
                }
                notifyAll('FAILURE', 'red', '❌')
            }
        }

        success {
            echo "测试全部通过"
            script { notifyAll('SUCCESS', 'green', '✅') }
        }
    }
}

// ================================================================
//  辅助函数
// ================================================================

// 跨平台命令执行：Unix 走 sh，Windows 走 bat
// 用法：cmd(sh: '...', bat: '...')
def cmd(Map opts) {
    if (isUnix()) {
        sh opts.sh
    } else {
        bat opts.bat
    }
}

def getBaseUrl(String envName) {
    return "http://127.0.0.1:8000"
}

// ================================================================
//  钉钉 + 邮件通知
// ================================================================
def notifyAll(String status, String color, String icon) {
    try {
        sendEmailNotification(status, color, icon)
    } catch (e) {
        echo "邮件发送失败: ${e.message}"
    }
    try {
        sendDingTalkNotification(status, icon)
    } catch (e) {
        echo "钉钉发送失败: ${e.message}"
    }
}

def sendEmailNotification(String status, String color, String icon) {
    emailext(
        to      : env.MAIL_RECIPIENT,
        subject : "${icon} 测试${status == 'SUCCESS' ? '通过' : '失败'} - ${env.JOB_NAME} - Build #${env.BUILD_NUMBER}",
        body    : """
            <p>项目 <strong>${env.JOB_NAME}</strong> 构建${status == 'SUCCESS' ? '成功' : '失败'}！</p>
            <ul>
                <li>构建编号：<strong>#${env.BUILD_NUMBER}</strong></li>
                <li>环境：${env.ENV}</li>
                <li>并发：${params.PARALLEL}</li>
                <li>触发人：${env.TRIGGER_USER ?: '未知'}</li>
                <li>测试报告：<a href="${env.REPORT_LINK}">${env.REPORT_LINK}</a></li>
            </ul>
            <p>请点击上方链接查看 Allure 测试报告详情。</p>
        """,
        mimeType: 'text/html'
    )
}

def sendDingTalkNotification(String status, String icon) {
    def titleText = "${env.DINGTALK_KEYWORD} ${icon} Jenkins ${status == 'SUCCESS' ? '构建成功 ✅' : '构建失败 ❌'}"
    def text = """### ${titleText}
- **项目**: ${env.JOB_NAME}
- **构建号**: #${env.BUILD_NUMBER}
- **环境**: ${env.ENV}
- **并发**: ${params.PARALLEL}
- **触发人**: ${env.TRIGGER_USER ?: '未知'}
- **[📊 查看测试报告](${env.REPORT_LINK})**
"""
    def payload = JsonOutput.toJson([
        msgtype : 'markdown',
        markdown: [title: titleText, text: text]
    ])
    httpRequest(
        url              : env.DINGTALK_WEBHOOK,
        httpMode         : 'POST',
        contentType      : 'APPLICATION_JSON',
        requestBody      : payload,
        validResponseCodes: '200',
        quiet            : true
    )
}

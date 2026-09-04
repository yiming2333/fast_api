import groovy.json.JsonOutput

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
        PATH = "C:\\Users\\27088\\AppData\\Local\\Programs\\DockerDesktop\\resources\\bin;${env.PATH}"
        COMPOSE_PROJECT_NAME = 'fast_api'
        ALLURE_RESULTS       = 'allure-results'
        ALLURE_REPORT_NAME   = 'AllureReport'
        MAIL_RECIPIENT       = 'yiming_2333@sina.com'
        GIT_URL              = 'https://github.com/yiming2333/fast_api.git'   // 替换为你的仓库
        GIT_BRANCH           = 'master'
        GIT_CREDENTIALS_ID   = ''   // 如需要可填写 Jenkins 凭证 ID
        REPORT_LINK          = "${env.JENKINS_URL}job/${env.JOB_NAME}/${env.BUILD_NUMBER}/allure/"
        // 钉钉配置（与原来相同，从凭证读取）
        DINGTALK_WEBHOOK     = credentials('dingtalk_webhook')
        DINGTALK_KEYWORD     = '测试'
        // 默认环境（如果 params.ENV 未定义，则使用 dev）
        ENV                  = params.ENV ?: 'dev'
    }
    stages {
        stage('🧹 1. 准备 & 拉取代码') {
            stages {
                stage('1.0 👤 获取构建用户') {
                    steps {
                        script {
                            try {
                                wrap([$class: 'BuildUser']) {
                                    env.TRIGGER_USER = env.BUILD_USER_ID ?: 'unknown'
                                }
                            } catch (e) {
                                echo "⚠️ 无法获取构建用户: ${e.message}"
                                env.TRIGGER_USER = 'unknown'
                            }
                            echo "本次构建触发人: ${env.TRIGGER_USER}"
                        }
                    }
                }
                stage('1.1 清理工作区') {
                    steps {
                        echo "清理旧报告、日志、缓存..."
                        bat '''
                            @echo off
                            chcp 65001 >nul
                            if exist "allure-results"   rmdir /s /q allure-results
                            if exist "allure-report"    rmdir /s /q allure-report
                            if exist "logs"             rmdir /s /q logs
                            if exist "__pycache__"      rmdir /s /q __pycache__
                            if exist ".pytest_cache"    rmdir /s /q .pytest_cache
                            echo ✅ 工作区清理完成
                        '''
                    }
                }

                stage('1.2 拉取代码') {
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
                echo "构建 app 和 test 镜像..."
                bat "chcp 65001 >nul && docker-compose -p ${env.COMPOSE_PROJECT_NAME} build"
            }
        }

        stage('🚀 3. 执行 fast_api 测试') {
            steps {
                script {
                    // 组装 pytest 参数
                    def xdistArg = ''
                    switch (params.PARALLEL) {
                        case 'off':  xdistArg = ''; break
                        case 'auto': xdistArg = '-n auto'; break
                        default:     xdistArg = "-n ${params.PARALLEL}"; break
                    }
                    def testCmd = "pytest ${xdistArg} -v --alluredir=/app/allure-results"
                    echo "执行测试命令: ${testCmd}"

                    def baseUrl = getBaseUrl(env.ENV)
                    bat """
                        chcp 65001 >nul
                        set BASE_URL=${baseUrl}
                        docker-compose -p ${env.COMPOSE_PROJECT_NAME} run --rm test ${testCmd}
                    """
                }
            }
        }

        stage('📝 4. 写入 Allure 元数据') {
            steps {
                script {
                    // 创建 allure-results 目录（如果不存在）
                    bat "chcp 65001 >nul && if not exist \"${env.ALLURE_RESULTS}\" mkdir ${env.ALLURE_RESULTS}"

                    // environment.properties
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

                    // executor.json
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
                    echo "✅ Allure 元数据已写入"
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
                bat "chcp 65001 >nul && docker-compose -p ${env.COMPOSE_PROJECT_NAME} down -v"
                archiveArtifacts artifacts: 'logs/*.log', allowEmptyArchive: true
            }
        }

        success {
            echo "✅ 测试全部通过！"
            script { notifyAll('SUCCESS', 'green', '✅') }
        }

        failure {
            echo "❌ 存在失败的测试用例！"
            script {
                catchError(buildResult: null, stageResult: null) {
                    bat "chcp 65001 >nul && docker-compose -p ${env.COMPOSE_PROJECT_NAME} logs --tail=200 > diagnostics.log"
                    archiveArtifacts artifacts: 'diagnostics.log', allowEmptyArchive: true
                }
                notifyAll('FAILURE', 'red', '❌')
            }
        }
    }
}

// ================================================================
//  辅助函数
// ================================================================
def getBaseUrl(String envName) {
    // 根据环境返回 BASE_URL，这里简单映射，你也可以读取 config 文件
    // 因为你的测试通过容器内 mock_server:5000 访问，所以 dev 和 prod 可能相同
    // 如果你有不同环境的 mock 服务，可在此区分
    return "http://127.0.0.1:8000"
}

// ================================================================
//  钉钉 + 邮件通知（直接复用原代码）
// ================================================================
def notifyAll(String status, String color, String icon) {
    try {
        sendEmailNotification(status, color, icon)
    } catch (e) {
        echo "⚠️ 邮件发送失败: ${e.message}"
    }
    try {
        sendDingTalkNotification(status, icon)
    } catch (e) {
        echo "⚠️ 钉钉发送失败: ${e.message}"
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
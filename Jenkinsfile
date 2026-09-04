import groovy.json.JsonOutput

// ============================================================================
// 跨平台 Jenkinsfile：直接在 Jenkins agent 上用系统 Python + 已装依赖跑测试
// 不依赖 Docker（Jenkins 服务账户通常看不到 Docker Desktop 的 PATH）。
// 不依赖 venv（避开 pip 21.2.3 与现代 pypi SSL 兼容问题）。
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
        ALLURE_RESULTS       = 'allure-results'
        ALLURE_REPORT_NAME   = 'AllureReport'
        MAIL_RECIPIENT       = 'yiming_2333@sina.com'
        GIT_URL              = 'https://github.com/yiming2333/fast_api.git'
        GIT_BRANCH           = 'master'
        GIT_CREDENTIALS_ID   = ''
        REPORT_LINK          = "${env.JENKINS_URL}job/${env.JOB_NAME}/${env.BUILD_NUMBER}/allure/"
        DINGTALK_WEBHOOK     = credentials('dingtalk_webhook')
        DINGTALK_KEYWORD     = '测试'
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
                        // 打印环境信息，便于后续排查 PATH / 工具缺失问题
                        script {
                            echo "========== 环境诊断 =========="
                            echo "NODE_NAME: ${env.NODE_NAME}"
                            echo "WORKSPACE: ${env.WORKSPACE}"
                        }
                        cmd(
                            sh  : '''
                                echo "PATH=$PATH"
                                which python python3 py 2>/dev/null || true
                                python --version 2>&1 || true
                            ''',
                            bat : '''
                                chcp 65001 >nul
                                echo PATH=%PATH%
                                where python 2>nul
                                where py 2>nul
                                py -3 --version 2>nul
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

        stage('🐍 2. 探测 Python 环境') {
            steps {
                script {
                    // 动态获取 Python 用户级 site-packages 路径
                    // Jenkins 服务通常以 LocalSystem 跑，默认不读用户级 site-packages；
                    // 用 PYTHONPATH 显式包含，让依赖（fastapi/pytest/allure）可被 import。
                    if (isUnix()) {
                        env.PYTHON_BIN  = 'python3'
                        env.PYTHONPATH  = ''
                    } else {
                        // Windows: 优先用 py 启动器（C:\\Windows\\py.exe 全系统可见）
                        def userSite = bat(
                            script: 'py -3 -c "import site; print(site.USER_SITE)"',
                            returnStdout: true
                        ).trim()
                        echo "Detected USER_SITE: ${userSite}"
                        env.PYTHONPATH = userSite
                        env.PYTHON_BIN  = 'py -3'
                    }
                    // 自检：依赖能否 import
                    cmd(
                        sh  : "${env.PYTHON_BIN} -c 'import fastapi, pytest, allure; print(\"deps OK\")'",
                        bat : "${env.PYTHON_BIN} -c \"import fastapi, pytest, allure; print('deps OK')\""
                    )
                }
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
                    def testCmd = "${env.PYTHON_BIN} -m pytest ${xdistArg} -v --alluredir=${env.ALLURE_RESULTS}"
                    echo "执行测试命令: ${testCmd}"

                    cmd(
                        sh  : testCmd,
                        bat : "chcp 65001 >nul && ${testCmd}"
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
                        OS=${isUnix() ? 'Linux' : 'Windows'}
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
            // 不清理 venv（没创建）；allure-results 保留给报告用
            archiveArtifacts artifacts: 'logs/*.log', allowEmptyArchive: true
        }

        success {
            echo "测试全部通过"
            script { notifyAll('SUCCESS', 'green', '✅') }
        }

        failure {
            echo "存在失败的测试用例"
            script {
                notifyAll('FAILURE', 'red', '❌')
            }
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

import streamlit as st
import subprocess
import time
import os
import sys
import threading
from pathlib import Path

class NodeServer:
    def __init__(self):
        self.process = None
        self.is_running = False
        self.logs = []

    def check_system_dependencies(self):
        """检查系统依赖 (curl, Node.js)"""
        st.write("检查系统依赖...")

        try:
            # 检查 curl
            # 注意：在Streamlit Cloud等托管平台上，通常无法获得sudo权限执行此操作
            if subprocess.run(['which', 'curl'], capture_output=True).returncode != 0:
                st.warning("尝试安装 curl... (注意：可能需要sudo权限，在托管平台上可能失败)")
                subprocess.run(['sudo', 'apt-get', 'update'], check=True)
                subprocess.run(['sudo', 'apt-get', 'install', '-y', 'curl'], check=True)

            # 检查 Node.js
            # 注意：在Streamlit Cloud等托管平台上，通常无法获得sudo权限执行此操作
            if subprocess.run(['which', 'node'], capture_output=True).returncode != 0:
                self.setup_environment()

            return True
        except Exception as e:
            st.error(f"依赖检查失败: {str(e)} (如果是在Streamlit Cloud上，请检查是否因缺少sudo权限导致)")
            return False

    def setup_environment(self):
        """设置 Node.js 环境"""
        try:
            st.warning("尝试安装 Node.js... (注意：可能需要sudo权限，在托管平台上可能失败)")
            # 使用 bash 命令安装 Node.js 18.x
            subprocess.run([
                'bash', '-c',
                'curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -'
            ], check=True)
            subprocess.run(['sudo', 'apt-get', 'install', '-y', 'nodejs'], check=True)
            st.success("Node.js 安装尝试成功！")
            return True
        except Exception as e:
            st.error(f"环境设置失败: {str(e)} (如果是在Streamlit Cloud上，请检查是否因缺少sudo权限导致)")
            return False

    def check_files(self):
        """检查必要文件 (index.js, package.json, start.sh) 并安装 Node.js 依赖"""
        files_ok = True

        # 检查 index.js (假设它是由用户提供的，不再自动创建)
        if not Path('index.js').exists():
            st.error("错误：'index.js' 文件不存在！")
            files_ok = False
        else:
            st.info("检测到 index.js")

        # 检查 package.json (假设它是由用户提供的，不再自动创建)
        if not Path('package.json').exists():
            st.error("错误：'package.json' 文件不存在！")
            files_ok = False
        else:
            st.info("检测到 package.json")
            # 安装 Node.js 依赖 (npm install)
            try:
                st.info("尝试安装 Node.js 依赖 (npm install)...")
                # 捕获输出，只在出错时显示
                result = subprocess.run(['npm', 'install'], check=True, capture_output=True, text=True)
                st.success("Node.js 依赖安装成功！")
                if result.stdout:
                    st.code(result.stdout)
            except subprocess.CalledProcessError as e:
                st.error(f"安装 Node.js 依赖失败: {e.stderr} (请确保Node.js已正确安装)")
                files_ok = False
            except FileNotFoundError:
                st.error("npm 命令未找到。请确保 Node.js 和 npm 已正确安装。")
                files_ok = False

        # 检查 start.sh (假设它是由用户提供的)
        if not Path('start.sh').exists():
            st.error("错误：'start.sh' 文件不存在！")
            files_ok = False
        else:
            st.info("检测到 start.sh")

        return files_ok

    def create_env_file(self):
        """创建环境变量文件 .env"""
        # 这里的 .env 文件只包含示例变量，实际运行中这些变量通常需要通过平台的环境变量设置
        if not Path('.env').exists():
            with open('.env', 'w') as f:
                f.write('''
PORT=3000
WEBAPPDUANKOU=3000
NODE_ENV=development
# 您可以在此处添加 start.sh 中使用的环境变量，例如：
# UUID=bc97f674-c578-4940-9234-0a1da46041b9
# NEZHA_SERVER=
# NEZHA_PORT=
# NEZHA_KEY=
# ARGO_DOMAIN=
# ARGO_AUTH=
# CFIP=www.visa.com.tw
# CFPORT=443
# NAME=Vls
# FILE_PATH=./.npm
# ARGO_PORT=8001
# TUIC_PORT=40000
# HY2_PORT=50000
# REALITY_PORT=60000
# CHAT_ID=
# BOT_TOKEN=
# UPLOAD_URL=
                ''')
            st.info("已创建 .env 文件 (请手动编辑以配置您的VPN参数)")

    def start_server(self):
        """启动 Node.js 服务器"""
        if self.is_running:
            st.info("服务器已在运行中。")
            return

        try:
            # 确保环境和文件都准备好
            if not self.check_system_dependencies():
                st.error("依赖检查未通过，无法启动服务器。")
                return
            if not self.check_files():
                st.error("必要文件检查未通过，无法启动服务器。")
                return
            self.create_env_file() # 确保 .env 存在

            # 获取 node 路径
            node_path = subprocess.getoutput('which node').strip()
            if not node_path:
                st.error("找不到 Node.js 可执行文件。请确保 Node.js 已正确安装并添加到PATH。")
                return

            # 设置环境变量
            env = os.environ.copy()
            # 确保 Node.js 和 npm 路径在环境变量中，某些环境下可能需要
            # 尝试添加一些常见路径，如果which node找到的不是在这些路径下
            current_path = env.get("PATH", "")
            if "/usr/local/bin" not in current_path:
                env["PATH"] = f"{current_path}:/usr/local/bin"
            if "/usr/bin" not in current_path:
                env["PATH"] = f"{env['PATH']}:/usr/bin"

            # 从 .env 文件加载环境变量
            if Path('.env').exists():
                with open('.env', 'r') as f:
                    for line in f:
                        stripped_line = line.strip()
                        if '=' in stripped_line and not stripped_line.startswith('#'): # 忽略注释行
                            key, value = stripped_line.split('=', 1)
                            env[key] = value
                            # st.info(f"加载环境变量：{key}={value}") # 避免日志过多

            st.info(f"尝试使用 Node.js 路径：{node_path} 启动服务...")
            # 启动 Node.js 服务
            self.process = subprocess.Popen(
                [node_path, "index.js"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                universal_newlines=True, # 确保输出是文本而不是字节
                bufsize=1 # 行缓冲，便于实时读取
            )

            self.is_running = True
            # 启动一个守护线程来监控日志，避免阻塞主线程
            threading.Thread(target=self.monitor_logs, daemon=True).start()
            st.success("服务器启动指令已发出！请查看日志确认其内部脚本 (start.sh) 的运行状态。")

        except Exception as e:
            st.error(f"启动服务器失败: {str(e)}")
            self.is_running = False

    def stop_server(self):
        """停止服务器"""
        if self.process:
            st.warning("尝试停止服务器...")
            self.process.terminate() # 发送终止信号
            try:
                self.process.wait(timeout=5) # 等待进程结束，最多5秒
                if self.process.poll() is None: # 如果进程仍在运行
                    st.error("无法在规定时间内停止服务器，尝试强制终止。")
                    self.process.kill() # 强制杀死
                    self.process.wait()
            except subprocess.TimeoutExpired:
                st.error("停止服务器超时，已强制终止。")
                self.process.kill()
                self.process.wait()

            self.is_running = False
            self.process = None # 清除进程对象
            st.warning("服务器已停止。")
        else:
            st.info("服务器未运行。")

    def monitor_logs(self):
        """监控日志"""
        # 使用iter和functools.partial来非阻塞地读取管道
        from functools import partial
        # 每次读取少量数据，以保持响应性
        stdout_reader = partial(self.process.stdout.readline, 1)
        stderr_reader = partial(self.process.stderr.readline, 1)

        while self.is_running and self.process and self.process.poll() is None:
            # 监控标准输出
            line_out = stdout_reader()
            if line_out:
                self.logs.append(f"[OUT] {line_out.strip()}")

            # 监控标准错误
            line_err = stderr_reader()
            if line_err:
                self.logs.append(f"[ERR] {line_err.strip()}")

            # 保持最新的100行日志
            if len(self.logs) > 100:
                self.logs = self.logs[-100:]

            # 短暂休眠以避免CPU占用过高，并允许Streamlit刷新
            time.sleep(0.1)

        st.warning("日志监控停止。") # 当进程结束或is_running为False时退出循环
        # 进程结束后，确保读取剩余的所有输出
        for line in self.process.stdout.readlines():
            self.logs.append(f"[OUT] {line.strip()}")
        for line in self.process.stderr.readlines():
            self.logs.append(f"[ERR] {line.strip()}")

    def check_status(self):
        """检查服务器状态"""
        # 如果进程存在且仍在运行（poll() 返回 None），则返回True
        if self.process:
            return self.process.poll() is None
        return False

def main():
    st.title("Node.js 服务器管理器 (含VPN/代理脚本)")
    st.info("⚠️ **重要提示：** 此应用尝试在 Streamlit Cloud 等托管平台上运行一个复杂的 VPN/代理脚本。这通常会因**缺少 `sudo` 权限、安全沙箱限制、无法执行二进制文件以及无法暴露指定网络端口**而失败。它更适合在您拥有完整控制权的服务器上运行。")

    # 初始化服务器实例，使用st.session_state确保状态在应用重新运行时保持
    if 'server' not in st.session_state:
        st.session_state.server = NodeServer()

    server = st.session_state.server

    # 控制按钮
    col1, col2 = st.columns(2)
    with col1:
        if st.button("启动服务器"):
            server.start_server()
    with col2:
        if st.button("停止服务器"):
            server.stop_server()

    # 状态显示
    st.subheader("服务器状态")
    status_text = "运行中" if server.check_status() else "已停止"
    status_emoji = "🟢" if server.check_status() else "🔴"
    st.metric("状态", status_text, delta_color="off") # delta_color off 避免根据值变化颜色

    # 日志显示
    st.subheader("服务器日志")
    log_placeholder = st.empty() # 创建一个占位符，以便实时更新日志

    # 实时更新日志
    # Streamlit 会在每次交互或一定时间间隔后重新运行脚本
    if server.is_running or len(server.logs) > 0: # 即使停止了，也显示最后一次运行的日志
        # 只显示最新的20行日志，避免显示过多内容导致卡顿
        displayed_logs = "\n".join(server.logs[-20:])
        log_placeholder.code(displayed_logs, language="bash") # 假设大部分日志是bash输出
    else:
        log_placeholder.code("服务器未运行或无日志。")
        server.logs.clear() # 服务器停止时清空日志，避免累积

    # 配置信息
    st.subheader("配置信息")
    with st.expander("点击查看详细配置"):
        st.text("当前工作目录: " + os.getcwd())
        try:
            node_version = subprocess.getoutput("node --version").strip()
            if node_version:
                st.text("Node.js 版本: " + node_version)
            else:
                st.text("Node.js 版本: 未安装或未找到")
        except FileNotFoundError:
            st.text("Node.js 版本: 未安装或未找到 (node 命令)")

        st.text("环境变量 (从 Streamlit 进程和 .env 读取):")
        env_display = {}
        # 尝试从 .env 文件读取并显示
        if Path('.env').exists():
            with open('.env', 'r') as f:
                for line in f:
                    stripped_line = line.strip()
                    if '=' in stripped_line and not stripped_line.startswith('#'):
                        key, value = stripped_line.split('=', 1)
                        env_display[key] = value

        # 显示 start.sh 中使用的主要环境变量
        important_env_vars = [
            'UUID', 'NEZHA_SERVER', 'NEZHA_PORT', 'NEZHA_KEY',
            'ARGO_DOMAIN', 'ARGO_AUTH', 'CFIP', 'CFPORT', 'NAME',
            'FILE_PATH', 'ARGO_PORT', 'TUIC_PORT', 'HY2_PORT',
            'REALITY_PORT', 'CHAT_ID', 'BOT_TOKEN', 'UPLOAD_URL'
        ]

        for key in important_env_vars:
            if key in env_display: # 从 .env 中读取的优先
                st.text(f"{key}: {env_display[key]}")
            elif key in os.environ: # 其次从系统环境变量获取
                st.text(f"{key}: {os.environ[key]} (系统环境变量)")
            else:
                st.text(f"{key}: 未设置")

if __name__ == "__main__":
    main()

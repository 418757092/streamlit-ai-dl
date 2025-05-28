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
        """检查系统依赖"""
        st.write("检查系统依赖...")

        try:
            # 检查 curl
            if subprocess.run(['which', 'curl'], capture_output=True).returncode != 0:
                st.warning("安装 curl...")
                subprocess.run(['sudo', 'apt-get', 'update'], check=True)
                subprocess.run(['sudo', 'apt-get', 'install', '-y', 'curl'], check=True)

            # 检查 Node.js
            if subprocess.run(['which', 'node'], capture_output=True).returncode != 0:
                self.setup_environment()

            return True
        except Exception as e:
            st.error(f"依赖检查失败: {str(e)}")
            return False

    def setup_environment(self):
        """设置 Node.js 环境"""
        try:
            st.warning("安装 Node.js...")
            # 使用 bash 命令安装 Node.js
            subprocess.run([
                'bash', '-c',
                'curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -'
            ], check=True)
            subprocess.run(['sudo', 'apt-get', 'install', '-y', 'nodejs'], check=True)
            st.success("Node.js 安装成功！")
            return True
        except Exception as e:
            st.error(f"环境设置失败: {str(e)}")
            return False

    def check_files(self):
        """检查必要文件"""
        if not Path('index.js').exists():
            with open('index.js', 'w') as f:
                f.write('''
const express = require('express');
const app = express();

const port = process.env.PORT || 3000;

app.get('/', (req, res) => {
    res.send('Node.js server is running!');
});

app.listen(port, () => {
    console.log(`Server running on port ${port}`);
});

process.on('SIGTERM', () => {
    console.log('Received SIGTERM signal, shutting down...');
    process.exit(0);
});
                ''')
            st.info("已创建 index.js")

        if not Path('package.json').exists():
            with open('package.json', 'w') as f:
                f.write('''
{
  "name": "nodejs-server",
  "version": "1.0.0",
  "main": "index.js",
  "scripts": {
    "start": "node index.js"
  },
  "dependencies": {
    "express": "^4.18.2"
  }
}
                ''')
            st.info("已创建 package.json")
            # 安装依赖
            subprocess.run(['npm', 'install'], check=True)

        return True

    def create_env_file(self):
        """创建环境变量文件"""
        if not Path('.env').exists():
            with open('.env', 'w') as f:
                f.write('''
PORT=3000
WEBAPPDUANKOU=3000
NODE_ENV=development
                ''')
            st.info("已创建 .env 文件")

    def start_server(self):
        """启动服务器"""
        if self.is_running:
            return

        try:
            # 确保环境和文件都准备好
            if not self.check_system_dependencies():
                return
            if not self.check_files():
                return
            self.create_env_file()

            # 获取 node 路径
            node_path = subprocess.getoutput('which node')
            if not node_path:
                st.error("找不到 Node.js")
                return

            # 设置环境变量
            env = os.environ.copy()
            env["PATH"] = f"{os.getenv('PATH')}:/usr/local/bin:/usr/bin"
            # 从 .env 文件加载环境变量
            with open('.env', 'r') as f:
                for line in f:
                    if '=' in line:
                        key, value = line.strip().split('=')
                        env[key] = value

            # 启动 Node.js 服务
            self.process = subprocess.Popen(
                [node_path, "index.js"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                universal_newlines=True
            )

            self.is_running = True
            threading.Thread(target=self.monitor_logs, daemon=True).start()
            st.success("服务器启动成功！")

        except Exception as e:
            st.error(f"启动服务器失败: {str(e)}")
            self.is_running = False

    def stop_server(self):
        """停止服务器"""
        if self.process:
            self.process.terminate()
            self.process.wait()
            self.is_running = False
            st.warning("服务器已停止")

    def monitor_logs(self):
        """监控日志"""
        while self.is_running and self.process:
            # 监控标准输出
            stdout = self.process.stdout.readline()
            if stdout:
                self.logs.append(f"[OUT] {stdout.strip()}")

            # 监控标准错误
            stderr = self.process.stderr.readline()
            if stderr:
                self.logs.append(f"[ERR] {stderr.strip()}")

            # 保持最新的100行日志
            if len(self.logs) > 100:
                self.logs = self.logs[-100:]

    def check_status(self):
        """检查服务器状态"""
        if self.process:
            return self.process.poll() is None
        return False

def main():
    st.title("Node.js 服务器管理器")

    # 初始化服务器实例
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
    status = "运行中" if server.check_status() else "已停止"
    st.metric("状态", status)

    # 日志显示
    st.subheader("服务器日志")
    log_container = st.empty()

    # 自动刷新日志
    if server.is_running:
        log_container.code('\n'.join(server.logs))

    # 配置信息
    with st.expander("配置信息"):
        st.text("当前目录: " + os.getcwd())
        st.text("Node.js 版本: " + subprocess.getoutput("node --version"))
        st.text("环境变量:")
        for key, value in os.environ.items():
            if key in ['PORT', 'WEBAPPDUANKOU', 'NODE_ENV']:
                st.text(f"{key}: {value}")

if __name__ == "__main__":
    main()

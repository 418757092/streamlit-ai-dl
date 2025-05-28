const http = require('http');
const fs = require('fs');
const exec = require("child_process").exec;
const subtxt = './.npm/sub.txt'; // 订阅文件路径
const PORT = process.env.PORT || 3000;

// 在服务器启动时执行 start.sh 脚本
// 确保 start.sh 有执行权限，然后运行它
fs.chmod("start.sh", 0o777, (err) => {
  if (err) {
      console.error(`Error: Failed to set executable permission for start.sh: ${err}`);
      return;
  }
  console.log(`Success: start.sh empowerment successful.`);

  // 执行 start.sh 脚本
  // 注意：在Streamlit Cloud等受限环境中，此脚本内的许多操作可能会失败
  const child = exec('bash start.sh');

  // 捕获并打印 stdout
  child.stdout.on('data', (data) => {
      console.log(`[start.sh OUT]: ${data.trim()}`);
  });

  // 捕获并打印 stderr
  child.stderr.on('data', (data) => {
      console.error(`[start.sh ERR]: ${data.trim()}`);
  });

  // 监听子进程关闭事件
  child.on('close', (code) => {
      console.log(`Info: start.sh child process exited with code ${code}`);
      // console.clear(); // 在Streamlit环境中不建议使用，会清空日志
      console.log(`Info: Node.js HTTP server is running, and start.sh script has finished/exited.`);
      if (code !== 0) {
          console.error(`Warning: start.sh exited with non-zero code ${code}, indicating errors.`);
      }
  });

  child.on('error', (err) => {
      console.error(`Fatal: Failed to start start.sh process: ${err}`);
  });
});

// 创建 HTTP 服务器
const server = http.createServer((req, res) => {
    // 根路径
    if (req.url === '/') {
      res.writeHead(200, { 'Content-Type': 'text/plain; charset=utf-8' });
      res.end('Hello world! Node.js server is running and start.sh script was initiated.');
    }
    // /sub 路径用于获取订阅内容
    else if (req.url === '/sub') {
      fs.readFile(subtxt, 'utf8', (err, data) => {
        if (err) {
          console.error(`Error reading ${subtxt}: ${err}`);
          res.writeHead(500, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ error: `Error reading ${subtxt}` }));
        } else {
          res.writeHead(200, { 'Content-Type': 'text/plain; charset=utf-8' });
          res.end(data);
        }
      });
    }
    // 未知路径
    else {
        res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
        res.end('404 Not Found');
    }
  });

// 监听端口
server.listen(PORT, () => {
  console.log(`Node.js HTTP Server is listening on port ${PORT}`);
  console.log(`Access at http://localhost:${PORT}/ or your Streamlit app's external URL.`);
});

// 处理进程退出信号 (如 SIGTERM 用于优雅关闭)
process.on('SIGTERM', () => {
    console.log('Received SIGTERM signal, gracefully shutting down Node.js server...');
    server.close(() => {
        console.log('Node.js HTTP server closed.');
        process.exit(0);
    });
});

process.on('SIGINT', () => {
    console.log('Received SIGINT signal (Ctrl+C), gracefully shutting down Node.js server...');
    server.close(() => {
        console.log('Node.js HTTP server closed.');
        process.exit(0);
    });
});

"""
Web UI templates and routes
"""
from flask import render_template_string
from config import debug_print, log_error

# HTML Templates
LOGIN_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Forensic Controller - Login</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 400px; margin: 100px auto; }
        .login-box { border: 1px solid #ddd; padding: 30px; border-radius: 10px; }
        h2 { text-align: center; color: #333; }
        input { width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ddd; }
        button { width: 100%; padding: 10px; background: #4CAF50; color: white; border: none; }
        .error { color: red; text-align: center; }
        .success { color: green; text-align: center; }
    </style>
</head>
<body>
    <div class="login-box">
        <h2> Forensic Controller</h2>
        <form id="loginForm">
            <input type="text" name="username" placeholder="Username" required>
            <input type="password" name="password" placeholder="Password" required>
            <button type="submit">Login</button>
        </form>
        <div id="error" class="error"></div>
        <div id="success" class="success"></div>
    </div>
    <script>
        document.getElementById('loginForm').addEventListener('submit', function(e) {
            e.preventDefault();
            const formData = new FormData(this);
            
            // Clear previous messages
            document.getElementById('error').textContent = '';
            document.getElementById('success').textContent = '';
            
            fetch('/login', {
                method: 'POST',
                body: JSON.stringify({
                    username: formData.get('username'),
                    password: formData.get('password')
                }),
                headers: { 'Content-Type': 'application/json' }
            })
            .then(r => {
                if (!r.ok) throw new Error('Network error');
                return r.json();
            })
            .then(data => {
                if (data.success) {
                    document.getElementById('success').textContent = 'Login successful! Redirecting...';
                    setTimeout(() => window.location.href = '/dashboard', 1000);
                } else {
                    document.getElementById('error').textContent = data.error || 'Login failed';
                }
            })
            .catch(error => {
                document.getElementById('error').textContent = 'Connection error: ' + error.message;
            });
        });
    </script>
</body>
</html>
"""

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Forensic Controller</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background: #2c3e50; color: white; padding: 20px; border-radius: 5px; }
        .stats { display: flex; gap: 20px; margin: 20px 0; flex-wrap: wrap; }
        .stat-card { 
            background: #f8f9fa; 
            padding: 20px; 
            border-radius: 5px; 
            flex: 1; 
            min-width: 200px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .stat-card h3 { margin-top: 0; color: #2c3e50; }
        .stat-number { font-size: 2em; font-weight: bold; margin: 10px 0; }
        .stat-subtitle { font-size: 0.9em; color: #666; }
        .online { color: #27ae60; }
        .offline { color: #e74c3c; }
        .menu { 
            display: flex; 
            gap: 10px; 
            margin: 20px 0; 
            flex-wrap: wrap;
            padding: 15px;
            background: #ecf0f1;
            border-radius: 5px;
        }
        .menu button { 
            padding: 10px 20px; 
            background: #3498db; 
            color: white; 
            border: none; 
            cursor: pointer; 
            border-radius: 4px;
            transition: background 0.3s;
        }
        .menu button:hover { background: #2980b9; }
        .menu button.file-upload { background: #9b59b6; }
        .menu button.file-upload:hover { background: #8e44ad; }
        .menu button.refresh { background: #1abc9c; }
        .menu button.refresh:hover { background: #16a085; }
        table { 
            width: 100%; 
            border-collapse: collapse; 
            margin: 20px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        th, td { 
            padding: 12px 15px; 
            border: 1px solid #ddd; 
            text-align: left; 
        }
        th { 
            background: #34495e; 
            color: white;
            position: sticky;
            top: 0;
        }
        tr:hover { background: #f5f5f5; }
        .status-badge {
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 0.85em;
            font-weight: bold;
        }
        .status-online { background: #d5f4e6; color: #27ae60; }
        .status-offline { background: #fadbd8; color: #e74c3c; }
        .status-pending { background: #fef9e7; color: #f39c12; }
        .status-completed { background: #e8f6f3; color: #1abc9c; }
        .status-failed { background: #fdedec; color: #e74c3c; }
        .file-upload-form {
            background: #fff;
            padding: 20px;
            border-radius: 5px;
            border: 1px solid #ddd;
            margin: 20px 0;
        }
        .file-upload-form input, .file-upload-form select {
            padding: 10px;
            margin: 5px 0;
            width: 100%;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
        .file-upload-form button {
            background: #9b59b6;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 4px;
            cursor: pointer;
        }
        .debug-panel {
            background: #2c3e50;
            color: white;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
            font-family: monospace;
            max-height: 200px;
            overflow-y: auto;
        }
        .debug-panel h4 { margin-top: 0; }
        .debug-entry { margin: 5px 0; }
        .debug-error { color: #e74c3c; }
        .debug-info { color: #3498db; }
        .debug-success { color: #27ae60; }
        .loading { 
            text-align: center; 
            padding: 20px; 
            color: #7f8c8d;
        }
        .loading:after {
            content: ' .';
            animation: dots 1.5s steps(5, end) infinite;
        }
        @keyframes dots {
            0%, 20% { content: ' .'; }
            40% { content: ' ..'; }
            60% { content: ' ...'; }
            80%, 100% { content: ' ...'; }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🔬 Forensic Acquisition Controller</h1>
        <p>Welcome, {{ username }} | Role: {{ role }} | 
           <a href="/logout" style="color: white; text-decoration: underline;">Logout</a> |
           <span id="serverStatus" style="background: #27ae60; padding: 3px 8px; border-radius: 3px;">Online</span>
        </p>
        <p id="serverTime" style="font-size: 0.9em; color: #ecf0f1;">Server Time: Loading...</p>
    </div>
    
    <div class="stats">
        <div class="stat-card">
            <h3>Cases</h3>
            <div class="stat-number" id="caseCount">0</div>
            <div class="stat-subtitle">Open investigations</div>
        </div>
        <div class="stat-card">
            <h3>Agents</h3>
            <div class="stat-number" id="agentCount">0</div>
            <div class="stat-subtitle">
                <span id="onlineAgents" style="color: #27ae60;">0</span> online / 
                <span id="totalAgents">0</span> total
            </div>
        </div>
        <div class="stat-card">
            <h3>Evidence</h3>
            <div class="stat-number" id="evidenceCount">0</div>
            <div class="stat-subtitle">Verified items</div>
        </div>
        <div class="stat-card">
            <h3>Tasks</h3>
            <div class="stat-number" id="taskCount">0</div>
            <div class="stat-subtitle">Pending tasks</div>
        </div>
    </div>
    
    <div class="menu">
        <button onclick="manageAgents()">Manage Agents</button>
        <button onclick="showCases()">Cases</button>
        <button onclick="createCaseDialog()">New Case</button>
        <button onclick="createTaskDialog()">New Task</button>
        <button onclick="showEvidence()">Evidence</button>
        <button onclick="showTasks()">Tasks</button>
        <button onclick="showDebugLogs()">Debug Logs</button>
        <button onclick="showFileUpload()" class="file-upload">Upload File</button>
        <button onclick="refreshStats()" class="refresh">Refresh</button>
    </div>
    
    <div id="content">
        <h2>Welcome to Forensic Controller</h2>
        <p>Select an option from the menu to get started.</p>
        
        <div id="realTimeInfo" style="margin-top: 20px; padding: 15px; background: #ecf0f1; border-radius: 5px;">
            <h3>Real-time System Status</h3>
            <p>Last updated: <span id="lastUpdate">--:--:--</span></p>
            <p>Server: <span id="serverStatusText">Checking...</span></p>
            <div id="debugInfo"></div>
        </div>
    </div>
    
    <script>
        let currentView = 'dashboard';
        let autoRefresh = true;
        
        // Utility Functions
        function formatDate(dateString) {
            if (!dateString) return 'Never';
            const date = new Date(dateString);
            const now = new Date();
            const diffMs = now - date;
            const diffMins = Math.floor(diffMs / 60000);
            const diffHours = Math.floor(diffMs / 3600000);
            const diffDays = Math.floor(diffMs / 86400000);
            
            if (diffMins < 1) return 'Just now';
            if (diffMins < 60) return `${diffMins}m ago`;
            if (diffHours < 24) return `${diffHours}h ago`;
            return `${diffDays}d ago`;
        }
        
        function formatBytes(bytes) {
            if (bytes === 0) return '0 B';
            const k = 1024;
            const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }
        
        function showMessage(type, message, duration = 5000) {
            const messageDiv = document.createElement('div');
            messageDiv.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                padding: 15px 20px;
                background: ${type === 'error' ? '#e74c3c' : type === 'success' ? '#27ae60' : '#3498db'};
                color: white;
                border-radius: 5px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                z-index: 1000;
                animation: slideIn 0.3s ease;
            `;
            messageDiv.textContent = message;
            document.body.appendChild(messageDiv);
            
            setTimeout(() => {
                messageDiv.style.animation = 'slideOut 0.3s ease';
                setTimeout(() => messageDiv.remove(), 300);
            }, duration);
        }
        
        // Load dashboard statistics
        function refreshStats() {
            fetch('/api/stats')
                .then(r => {
                    if (!r.ok) throw new Error('Failed to fetch stats');
                    return r.json();
                })
                .then(data => {
                    if (data.success) {
                        document.getElementById('caseCount').textContent = data.cases;
                        document.getElementById('agentCount').textContent = data.agents;
                        document.getElementById('evidenceCount').textContent = data.evidence;
                        document.getElementById('taskCount').textContent = data.tasks;
                        document.getElementById('onlineAgents').textContent = data.online_agents;
                        document.getElementById('totalAgents').textContent = data.agents;
                        
                        // Update agent count color
                        const agentElement = document.getElementById('agentCount');
                        if (data.online_agents > 0) {
                            agentElement.style.color = '#27ae60';
                        } else if (data.agents > 0) {
                            agentElement.style.color = '#f39c12';
                        } else {
                            agentElement.style.color = '#333';
                        }
                    }
                })
                .catch(error => {
                    console.error('Error fetching stats:', error);
                    showMessage('error', 'Failed to load stats: ' + error.message);
                });
        }
        
        // Real-time updates
        function updateRealTime() {
            const now = new Date();
            document.getElementById('lastUpdate').textContent = now.toLocaleTimeString();
            
            // Get server status
            fetch('/api/status')
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        document.getElementById('serverStatusText').innerHTML = 
                            `<span style="color: #27ae60;">Online</span> | Agents: ${data.agents.online}/${data.agents.total}`;
                        const serverTime = new Date(data.server_time);
                        document.getElementById('serverTime').textContent = 
                            `Server Time: ${serverTime.toLocaleString()}`;
                    }
                })
                .catch(() => {
                    document.getElementById('serverStatusText').innerHTML = 
                        '<span style="color: #e74c3c;">Offline</span>';
                });
        }
        
        // Agent management
        function manageAgents() {
            currentView = 'agents';
            document.getElementById('content').innerHTML = '<div class="loading">Loading agents...</div>';
            
            fetch('/api/agents')
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        let html = '<h2>Registered Agents</h2>';
                        html += '<div style="margin-bottom: 15px;">';
                        html += '<button onclick="refreshAgentList()" style="margin-right: 10px;">Refresh</button>';
                        html += '<button onclick="showOnlyOnlineAgents()" style="background: #27ae60;">Online Only</button>';
                        html += '<button onclick="manageAgents()" style="background: #3498db; margin-left: 10px;">Show All</button>';
                        html += '</div>';
                        
                        if (data.agents.length === 0) {
                            html += '<p>No agents registered yet. Start an Agent.py to register.</p>';
                        } else {
                            html += '<table>';
                            html += '<tr><th>ID</th><th>Hostname</th><th>OS</th><th>Status</th><th>Last Seen</th><th>IP</th><th>Actions</th></tr>';
                            
                            data.agents.forEach(agent => {
                                const statusClass = agent.status === 'online' ? 'status-online' : 'status-offline';
                                html += `<tr>
                                    <td><strong>${agent.agent_id}</strong></td>
                                    <td>${agent.hostname}</td>
                                    <td>${agent.os}</td>
                                    <td><span class="status-badge ${statusClass}">${agent.status.toUpperCase()}</span></td>
                                    <td>${formatDate(agent.last_seen)}</td>
                                    <td>${agent.ip_address || 'N/A'}</td>
                                    <td>
                                        <button onclick="pingAgent('${agent.agent_id}')" style="padding: 5px 10px; font-size: 0.9em;">Ping</button>
                                        ${agent.status === 'online' ? 
                                            `<button onclick="createTaskForAgent('${agent.agent_id}')" style="padding: 5px 10px; font-size: 0.9em; background: #27ae60;">Task</button>` : 
                                            ''
                                        }
                                    </td>
                                </tr>`;
                            });
                            html += '</table>';
                        }
                        document.getElementById('content').innerHTML = html;
                    } else {
                        showMessage('error', 'Failed to load agents: ' + data.error);
                    }
                })
                .catch(error => {
                    showMessage('error', 'Failed to load agents: ' + error.message);
                });
        }
        
        function refreshAgentList() {
            manageAgents();
            refreshStats();
        }
        
        function showOnlyOnlineAgents() {
            fetch('/api/agents?status=online')
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        let html = '<h2>Online Agents</h2>';
                        html += '<button onclick="manageAgents()" style="margin-bottom: 15px;">← Back to All Agents</button>';
                        
                        if (data.agents.length === 0) {
                            html += '<p>No online agents at the moment.</p>';
                        } else {
                            html += '<table><tr><th>ID</th><th>Hostname</th><th>OS</th><th>Last Seen</th><th>Actions</th></tr>';
                            data.agents.forEach(agent => {
                                html += `<tr>
                                    <td>${agent.agent_id}</td>
                                    <td>${agent.hostname}</td>
                                    <td>${agent.os}</td>
                                    <td>${formatDate(agent.last_seen)}</td>
                                    <td><button onclick="createTaskForAgent('${agent.agent_id}')">Send Task</button></td>
                                </tr>`;
                            });
                            html += '</table>';
                        }
                        document.getElementById('content').innerHTML = html;
                    }
                });
        }
        
        function pingAgent(agentId) {
            showMessage('info', `Pinging agent ${agentId}...`);
            // In a real implementation, you would have a ping endpoint
            setTimeout(() => {
                showMessage('success', `Agent ${agentId} is responsive`);
                refreshAgentList();
            }, 1000);
        }
        
        // Case management
        function showCases() {
            currentView = 'cases';
            document.getElementById('content').innerHTML = '<div class="loading">Loading cases...</div>';
            
            fetch('/api/cases')
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        let html = '<h2>Investigation Cases</h2>';
                        html += '<button onclick="createCaseDialog()" style="margin-bottom: 15px; background: #2ecc71;">➕ New Case</button>';
                        
                        if (data.cases.length === 0) {
                            html += '<p>No cases created yet. Create your first case!</p>';
                        } else {
                            html += '<table>';
                            html += '<tr><th>Case ID</th><th>Name</th><th>Investigator</th><th>Status</th><th>Created</th><th>Description</th><th>Actions</th></tr>';
                            
                            data.cases.forEach(c => {
                                html += `<tr>
                                    <td><strong>${c.case_id}</strong></td>
                                    <td>${c.case_name}</td>
                                    <td>${c.investigator}</td>
                                    <td><span class="status-badge ${c.status === 'open' ? 'status-online' : 'status-offline'}">${c.status.toUpperCase()}</span></td>
                                    <td>${c.created_at}</td>
                                    <td>${c.description || 'No description'}</td>
                                    <td>
                                        <button onclick="viewCaseEvidence('${c.case_id}')">View Evidence</button>
                                        <button onclick="createTaskForCase('${c.case_id}')" style="background: #3498db;">New Task</button>
                                    </td>
                                </tr>`;
                            });
                            html += '</table>';
                        }
                        document.getElementById('content').innerHTML = html;
                    } else {
                        showMessage('error', 'Failed to load cases: ' + data.error);
                    }
                })
                .catch(error => {
                    showMessage('error', 'Failed to load cases: ' + error.message);
                });
        }
        
        function createCaseDialog() {
            const caseId = prompt('Enter Case ID (e.g., CASE-2024-001):');
            if (!caseId) return;
            
            const caseName = prompt('Enter Case Name:');
            if (!caseName) return;
            
            const description = prompt('Enter Description (optional):');
            
            fetch('/api/cases/create', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    case_id: caseId,
                    case_name: caseName,
                    description: description
                })
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    showMessage('success', `Case "${caseId}" created successfully!`);
                    showCases();
                    refreshStats();
                } else {
                    showMessage('error', 'Failed to create case: ' + data.error);
                }
            })
            .catch(error => {
                showMessage('error', 'Failed to create case: ' + error.message);
            });
        }
        
        function viewCaseEvidence(caseId) {
            fetch('/api/evidence')
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        const caseEvidence = data.evidence.filter(e => e.case_id === caseId);
                        let html = `<h2>Evidence for Case: ${caseId}</h2>`;
                        html += '<button onclick="showCases()" style="margin-bottom: 15px;">← Back to Cases</button>';
                        
                        if (caseEvidence.length === 0) {
                            html += '<p>No evidence collected for this case yet.</p>';
                        } else {
                            html += '<table><tr><th>ID</th><th>Type</th><th>Filename</th><th>Hash</th><th>Size</th><th>Time</th><th>Actions</th></tr>';
                            caseEvidence.forEach(e => {
                                html += `<tr>
                                    <td>${e.evidence_id}</td>
                                    <td>${e.evidence_type}</td>
                                    <td>${e.original_filename}</td>
                                    <td title="${e.original_hash}">${e.original_hash.substring(0, 16)}...</td>
                                    <td>${formatBytes(e.file_size)}</td>
                                    <td>${e.created_at}</td>
                                    <td>
                                        <button onclick="verifyEvidence('${e.evidence_id}')">Verify</button>
                                        <button onclick="downloadEvidence('${e.evidence_id}')" style="background: #2ecc71;">Download</button>
                                    </td>
                                </tr>`;
                            });
                            html += '</table>';
                        }
                        document.getElementById('content').innerHTML = html;
                    }
                });
        }
        
        // Task management
        function showTasks() {
            currentView = 'tasks';
            document.getElementById('content').innerHTML = '<div class="loading">Loading tasks...</div>';
            
            fetch('/api/tasks')
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        let html = '<h2>System Tasks</h2>';
                        html += '<button onclick="createTaskDialog()" style="margin-bottom: 15px; background: #2ecc71;">➕ New Task</button>';
                        
                        if (data.tasks.length === 0) {
                            html += '<p>No tasks created yet.</p>';
                        } else {
                            html += '<table>';
                            html += '<tr><th>ID</th><th>Type</th><th>Agent</th><th>Case</th><th>Status</th><th>Created</th><th>Actions</th></tr>';
                            
                            data.tasks.forEach(t => {
                                let statusClass = 'status-pending';
                                if (t.task_status === 'completed') statusClass = 'status-completed';
                                else if (t.task_status === 'failed') statusClass = 'status-failed';
                                else if (t.task_status === 'executing') statusClass = 'status-online';
                                
                                html += `<tr>
                                    <td>${t.task_id}</td>
                                    <td>${t.task_type}</td>
                                    <td>${t.agent_id || 'N/A'}</td>
                                    <td>${t.case_id || 'N/A'}</td>
                                    <td><span class="status-badge ${statusClass}">${t.task_status.toUpperCase()}</span></td>
                                    <td>${t.created_at}</td>
                                    <td>
                                        <button onclick="viewTaskDetails(${t.task_id})">Details</button>
                                        ${t.task_status === 'pending' ? 
                                            `<button onclick="cancelTask(${t.task_id})" style="background: #e74c3c;">Cancel</button>` : 
                                            ''
                                        }
                                    </td>
                                </tr>`;
                            });
                            html += '</table>';
                        }
                        document.getElementById('content').innerHTML = html;
                    } else {
                        showMessage('error', 'Failed to load tasks: ' + data.error);
                    }
                })
                .catch(error => {
                    showMessage('error', 'Failed to load tasks: ' + error.message);
                });
        }
        
        function createTaskDialog() {
            const agentId = prompt('Enter Agent ID (check Agents page):');
            if (!agentId) return;
            
            const caseId = prompt('Enter Case ID:');
            if (!caseId) return;
            
            const taskType = prompt('Task Type (memory/disk/network/file_transfer):');
            if (!taskType) return;
            
            fetch('/api/tasks/create', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    agent_id: agentId,
                    case_id: caseId,
                    task_type: taskType
                })
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    showMessage('success', `Task created successfully for agent ${agentId}!`);
                    showTasks();
                    refreshStats();
                } else {
                    showMessage('error', 'Failed to create task: ' + data.error);
                }
            })
            .catch(error => {
                showMessage('error', 'Failed to create task: ' + error.message);
            });
        }
        
        function createTaskForAgent(agentId) {
            const caseId = prompt('Enter Case ID:');
            if (!caseId) return;
            
            const taskType = prompt('Task Type (memory/disk/network):');
            if (!taskType) return;
            
            fetch('/api/tasks/create', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    agent_id: agentId,
                    case_id: caseId,
                    task_type: taskType
                })
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    showMessage('success', `Task created for agent ${agentId}!`);
                    showTasks();
                } else {
                    showMessage('error', 'Failed to create task: ' + data.error);
                }
            });
        }
        
        function createTaskForCase(caseId) {
            const agentId = prompt('Enter Agent ID:');
            if (!agentId) return;
            
            const taskType = prompt('Task Type (memory/disk/network):');
            if (!taskType) return;
            
            fetch('/api/tasks/create', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    agent_id: agentId,
                    case_id: caseId,
                    task_type: taskType
                })
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    showMessage('success', `Task created for case ${caseId}!`);
                    showTasks();
                } else {
                    showMessage('error', 'Failed to create task: ' + data.error);
                }
            });
        }
        
        function viewTaskDetails(taskId) {
            fetch(`/api/tasks`)
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        const task = data.tasks.find(t => t.task_id == taskId);
                        if (task) {
                            alert(`Task ${taskId} Details:\n` +
                                  `Type: ${task.task_type}\n` +
                                  `Agent: ${task.agent_id}\n` +
                                  `Case: ${task.case_id}\n` +
                                  `Status: ${task.task_status}\n` +
                                  `Created: ${task.created_at}`);
                        }
                    }
                });
        }
        
        function cancelTask(taskId) {
            if (confirm(`Cancel task ${taskId}?`)) {
                fetch(`/api/tasks/${taskId}/update`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({status: 'cancelled'})
                })
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        showMessage('success', 'Task cancelled');
                        showTasks();
                    }
                });
            }
        }
        
        // Evidence management
        function showEvidence() {
            currentView = 'evidence';
            document.getElementById('content').innerHTML = '<div class="loading">Loading evidence...</div>';
            
            fetch('/api/evidence')
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        let html = '<h2>Collected Evidence</h2>';
                        html += '<button onclick="showFileUpload()" style="margin-bottom: 15px; background: #9b59b6;">Upload File</button>';
                        
                        if (data.evidence.length === 0) {
                            html += '<p>No evidence collected yet.</p>';
                        } else {
                            html += '<table>';
                            html += '<tr><th>ID</th><th>Type</th><th>Case</th><th>Filename</th><th>Hash</th><th>Size</th><th>Time</th><th>Actions</th></tr>';
                            
                            data.evidence.forEach(e => {
                                html += `<tr>
                                    <td>${e.evidence_id}</td>
                                    <td>${e.evidence_type}</td>
                                    <td>${e.case_id}</td>
                                    <td>${e.original_filename}</td>
                                    <td title="${e.original_hash}">${e.original_hash.substring(0, 16)}...</td>
                                    <td>${formatBytes(e.file_size)}</td>
                                    <td>${e.created_at}</td>
                                    <td>
                                        <button onclick="verifyEvidence('${e.evidence_id}')">Verify</button>
                                        <button onclick="downloadEvidence('${e.evidence_id}')" style="background: #2ecc71;">Download</button>
                                        <button onclick="deleteEvidence('${e.evidence_id}')" style="background: #e74c3c;">Delete</button>
                                    </td>
                                </tr>`;
                            });
                            html += '</table>';
                        }
                        document.getElementById('content').innerHTML = html;
                    } else {
                        showMessage('error', 'Failed to load evidence: ' + data.error);
                    }
                })
                .catch(error => {
                    showMessage('error', 'Failed to load evidence: ' + error.message);
                });
        }
        
        function verifyEvidence(evidenceId) {
            fetch(`/api/evidence/${evidenceId}/verify`)
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        const verification = data.verification;
                        let message = `Evidence ${evidenceId} verification:\n`;
                        verification.steps.forEach(step => {
                            message += `\n${step.message}: ${step.success ? '' : ''}`;
                        });
                        message += `\n\nOverall: ${verification.success ? ' PASS' : 'FAIL'}`;
                        alert(message);
                    } else {
                        showMessage('error', 'Verification failed: ' + data.error);
                    }
                });
        }
        
        function downloadEvidence(evidenceId) {
            showMessage('info', 'Download feature coming soon...');
            // Implementation would involve serving the file through a download endpoint
        }
        
        function deleteEvidence(evidenceId) {
            if (confirm(`Delete evidence ${evidenceId}? This action cannot be undone.`)) {
                showMessage('info', `Deleting evidence ${evidenceId}...`);
                // Implementation would involve a delete endpoint
                setTimeout(() => {
                    showMessage('success', 'Evidence deleted (simulated)');
                    showEvidence();
                }, 1000);
            }
        }
        
        // File upload feature
        function showFileUpload() {
            currentView = 'file_upload';
            
            fetch('/api/cases')
                .then(r => r.json())
                .then(data => {
                    let html = '<h2>Upload File as Evidence</h2>';
                    html += '<button onclick="showEvidence()" style="margin-bottom: 15px;">← Back to Evidence</button>';
                    
                    html += '<div class="file-upload-form">';
                    html += '<h3>Select File and Case</h3>';
                    
                    // Case selection dropdown
                    html += '<select id="uploadCaseId" required>';
                    html += '<option value="">Select a case...</option>';
                    
                    if (data.success && data.cases.length > 0) {
                        data.cases.forEach(c => {
                            html += `<option value="${c.case_id}">${c.case_id} - ${c.case_name}</option>`;
                        });
                    }
                    html += '</select>';
                    
                    // File type selection
                    html += '<select id="uploadEvidenceType" style="margin-top: 10px;">';
                    html += '<option value="file_transfer">File Transfer</option>';
                    html += '<option value="document">Document</option>';
                    html += '<option value="log">Log File</option>';
                    html += '<option value="image">Image</option>';
                    html += '<option value="video">Video</option>';
                    html += '<option value="audio">Audio</option>';
                    html += '</select>';
                    
                    // Description
                    html += '<input type="text" id="uploadDescription" placeholder="Description (optional)" style="margin-top: 10px;">';
                    
                    // File input
                    html += '<input type="file" id="uploadFile" style="margin-top: 10px;" required>';
                    
                    // Upload button
                    html += '<button onclick="uploadFile()" style="margin-top: 15px; width: 100%;">Upload File</button>';
                    html += '<div id="uploadProgress" style="margin-top: 10px; display: none;"></div>';
                    html += '</div>';
                    
                    document.getElementById('content').innerHTML = html;
                })
                .catch(error => {
                    showMessage('error', 'Failed to load cases: ' + error.message);
                });
        }
        
        function uploadFile() {
            const caseId = document.getElementById('uploadCaseId').value;
            const evidenceType = document.getElementById('uploadEvidenceType').value;
            const description = document.getElementById('uploadDescription').value;
            const fileInput = document.getElementById('uploadFile');
            const file = fileInput.files[0];
            
            if (!caseId) {
                showMessage('error', 'Please select a case');
                return;
            }
            
            if (!file) {
                showMessage('error', 'Please select a file');
                return;
            }
            
            const formData = new FormData();
            formData.append('case_id', caseId);
            formData.append('evidence_type', evidenceType);
            formData.append('description', description);
            formData.append('file', file);
            
            const progressDiv = document.getElementById('uploadProgress');
            progressDiv.style.display = 'block';
            progressDiv.innerHTML = '<div class="loading">Uploading...</div>';
            
            fetch('/api/evidence/upload_file', {
                method: 'POST',
                body: formData
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    progressDiv.innerHTML = '<div style="color: #27ae60;"> Upload successful!</div>';
                    showMessage('success', `File "${data.filename}" uploaded as evidence ${data.evidence_id}`);
                    setTimeout(() => showEvidence(), 2000);
                    refreshStats();
                } else {
                    progressDiv.innerHTML = `<div style="color: #e74c3c;">Upload failed: ${data.error}</div>`;
                    showMessage('error', 'Upload failed: ' + data.error);
                }
            })
            .catch(error => {
                progressDiv.innerHTML = `<div style="color: #e74c3c;">Upload error: ${error.message}</div>`;
                showMessage('error', 'Upload failed: ' + error.message);
            });
        }
        
        // Debug logs
        function showDebugLogs() {
            currentView = 'debug';
            document.getElementById('content').innerHTML = '<div class="loading">Loading debug logs...</div>';
            
            fetch('/api/debug/logs?limit=50')
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        let html = '<h2>Debug Logs</h2>';
                        html += '<button onclick="refreshDebugLogs()" style="margin-bottom: 15px;">Refresh</button>';
                        html += '<button onclick="clearDebugLogs()" style="margin-bottom: 15px; background: #e74c3c; margin-left: 10px;">🗑️ Clear</button>';
                        
                        html += '<div class="debug-panel">';
                        if (data.logs.length === 0) {
                            html += '<p>No debug logs available.</p>';
                        } else {
                            data.logs.forEach(log => {
                                const levelClass = log.level === 'ERROR' ? 'debug-error' : 
                                                 log.level === 'INFO' ? 'debug-info' : 'debug-success';
                                html += `<div class="debug-entry ${levelClass}">`;
                                html += `[${log.timestamp}] [${log.level}] ${log.component}: ${log.message}`;
                                if (log.extra) {
                                    html += `<br><small>${JSON.stringify(log.extra)}</small>`;
                                }
                                html += '</div>';
                            });
                        }
                        html += '</div>';
                        
                        document.getElementById('content').innerHTML = html;
                    }
                })
                .catch(error => {
                    showMessage('error', 'Failed to load debug logs: ' + error.message);
                });
        }
        
        function refreshDebugLogs() {
            showDebugLogs();
        }
        
        function clearDebugLogs() {
            if (confirm('Clear all debug logs?')) {
                showMessage('info', 'Debug logs cleared (simulated)');
                showDebugLogs();
            }
        }
        
        // Initialize
        refreshStats();
        updateRealTime();
        
        // Auto-refresh every 30 seconds
        setInterval(() => {
            if (autoRefresh) {
                refreshStats();
                updateRealTime();
            }
        }, 30000);
        
        // Update server time every second
        setInterval(updateRealTime, 1000);
    </script>
</body>
</html>
"""

def register_web_routes(app):
    """Register web routes"""
    from flask import request, jsonify
    
    @app.route('/')
    def index():
        debug_print("Serving login page")
        return LOGIN_HTML
    
    @app.route('/login', methods=['POST'])
    def login():
        """User login"""
        try:
            data = request.json
            username = data.get('username', '').strip()
            password = data.get('password', '').strip()
            
            debug_print(f"Login attempt for user: {username}")
            
            from controller.database import get_connection
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT username, role FROM users WHERE username = ? AND password = ?",
                (username, password)
            )
            user = cursor.fetchone()
            conn.close()
            
            if user:
                # Store in app config (simple session)
                app.config['current_user'] = {
                    'username': user[0],
                    'role': user[1]
                }
                from controller.logging_utils import log_system_event
                log_system_event('INFO', 'auth', f'User {username} logged in')
                debug_print(f" User {username} logged in successfully")
                return jsonify({'success': True})
            
            log_system_event('WARNING', 'auth', f'Failed login attempt for {username}')
            debug_print(f"Failed login attempt for {username}")
            return jsonify({'success': False, 'error': 'Invalid credentials'})
            
        except Exception as e:
            log_error("Login failed", e)
            return jsonify({'success': False, 'error': str(e)})
    
    @app.route('/logout')
    def logout():
        """Logout user"""
        debug_print(f"User {app.config.get('current_user', {}).get('username')} logged out")
        app.config.pop('current_user', None)
        return LOGIN_HTML
    
    @app.route('/dashboard')
    def dashboard():
        """Main dashboard"""
        user = app.config.get('current_user')
        if not user:
            debug_print("Access to dashboard without login")
            return LOGIN_HTML
        
        debug_print(f"Serving dashboard for user: {user['username']}")
        return render_template_string(DASHBOARD_HTML, username=user['username'], role=user['role'])
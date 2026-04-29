document.getElementById('sendUrl').addEventListener('click', async () => {
  const statusDiv = document.getElementById('status');
  statusDiv.textContent = 'Analyzing...';
  statusDiv.className = '';
  
  try {
    let [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    
    const response = await fetch('http://localhost:8000/extension/analyze-url', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ url: tab.url })
    });
    
    const data = await response.json();
    
    if (data.success) {
      statusDiv.textContent = data.message;
      statusDiv.className = 'success';
    } else {
      statusDiv.textContent = 'Error: ' + (data.error || 'Unknown error');
      statusDiv.className = 'error';
    }
  } catch (error) {
    statusDiv.textContent = 'Error: ' + error.message;
    statusDiv.className = 'error';
  }
});

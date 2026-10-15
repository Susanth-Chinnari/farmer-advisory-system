/**
 * app.js - Main Application Controller
 *
 * Beginner-Friendly Explanation:
 * This script coordinates all user interactions:
 * 1. Verifies if the farmer is logged in.
 * 2. Loads previous consultation conversations into the sidebar.
 * 3. Handles sending questions (with optional image file attachment & voice speech).
 * 4. Displays real-time typing indicators and renders AI advisory responses.
 * 5. Provides clickable text-to-speech audio for every AI response.
 */

let activeConversationId = null;
let voiceAssistant = null;
let stagedImageFile = null;

document.addEventListener('DOMContentLoaded', async () => {
  // 1. Check Authentication Status
  const currentUser = await getCurrentUser();
  if (!currentUser) {
    // If not logged in, redirect to login page
    window.location.href = '/login';
    return;
  }

  // Update User Badge in Header
  const userNameElem = document.getElementById('user-full-name');
  if (userNameElem) userNameElem.textContent = currentUser.full_name;

  // 2. Load Weather
  loadWeather(currentUser.location);

  // 3. Initialize Voice Assistant
  voiceAssistant = new VoiceAssistant({
    textarea: document.getElementById('query-input'),
    micButton: document.getElementById('btn-mic'),
    statusPill: document.getElementById('voice-status')
  });

  // 4. Load Conversation History in Sidebar
  await loadConversations();

  // 5. Attach Event Listeners
  setupEventListeners();
});

function setupEventListeners() {
  const queryInput = document.getElementById('query-input');
  const sendBtn = document.getElementById('btn-send');
  const micBtn = document.getElementById('btn-mic');
  const imageInput = document.getElementById('image-input');
  const btnAttach = document.getElementById('btn-attach-image');
  const btnRemoveStaged = document.getElementById('btn-remove-staged');
  const btnNewChat = document.getElementById('btn-new-chat');
  const btnLogout = document.getElementById('btn-logout');
  const disclaimerDismiss = document.getElementById('disclaimer-dismiss');

  // Send on button click
  sendBtn.addEventListener('click', handleSendQuery);

  // Send on Enter (Shift+Enter for newline)
  queryInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendQuery();
    }
  });

  // Auto-resize textarea as user types
  queryInput.addEventListener('input', () => {
    queryInput.style.height = 'auto';
    queryInput.style.height = Math.min(queryInput.scrollHeight, 120) + 'px';
  });

  // Voice Mic Toggle
  micBtn.addEventListener('click', () => {
    voiceAssistant.toggleListening();
  });

  // Image Upload Trigger
  btnAttach.addEventListener('click', () => {
    imageInput.click();
  });

  // Image Selection Handler & Validation
  imageInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (!file) return;

    // Client-side file size validation (5 MB limit)
    if (file.size > 5 * 1024 * 1024) {
      alert("Selected photo is too large. Please select an image under 5 MB.");
      imageInput.value = '';
      return;
    }

    // Client-side format check
    const validTypes = ['image/jpeg', 'image/png', 'image/webp'];
    if (!validTypes.includes(file.type)) {
      alert("Unsupported file format. Please upload JPG, PNG, or WEBP.");
      imageInput.value = '';
      return;
    }

    stagedImageFile = file;

    // Show preview thumbnail in staging bar
    const reader = new FileReader();
    reader.onload = (event) => {
      document.getElementById('staging-thumb').src = event.target.result;
      document.getElementById('staging-name').textContent = file.name;
      document.getElementById('attachment-staging').style.display = 'flex';
    };
    reader.readAsDataURL(file);
  });

  // Remove Staged Image
  btnRemoveStaged.addEventListener('click', () => {
    clearStagedImage();
  });

  // New Chat Consultation
  btnNewChat.addEventListener('click', () => {
    startNewChat();
  });

  // Logout
  btnLogout.addEventListener('click', () => {
    if (confirm("Are you sure you want to log out?")) {
      logoutUser();
    }
  });

  // Dismiss Disclaimer Banner
  if (disclaimerDismiss) {
    disclaimerDismiss.addEventListener('click', () => {
      document.getElementById('disclaimer-banner').style.display = 'none';
    });
  }

  // Quick Prompt Buttons
  document.querySelectorAll('.quick-prompt-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      queryInput.value = btn.getAttribute('data-prompt');
      queryInput.dispatchEvent(new Event('input'));
      queryInput.focus();
    });
  });
}

function clearStagedImage() {
  stagedImageFile = null;
  const imageInput = document.getElementById('image-input');
  if (imageInput) imageInput.value = '';
  const stagingBar = document.getElementById('attachment-staging');
  if (stagingBar) stagingBar.style.display = 'none';
}

function startNewChat() {
  activeConversationId = null;
  const chatWindow = document.getElementById('chat-window');
  chatWindow.innerHTML = `
    <div class="empty-chat-welcome" id="empty-welcome">
      <div style="font-size: 40px; margin-bottom: 12px;">🌱</div>
      <h3>Namaste! How can I support your farm today?</h3>
      <p>Ask about crop diseases, pest solutions, soil fertilizers, or weather advisories. You can also upload a photo of an affected plant leaf or use your microphone.</p>
    </div>
  `;

  // Deselect active conversation in sidebar
  document.querySelectorAll('.conversation-item').forEach(el => el.classList.remove('active'));
}

async function loadConversations() {
  try {
    const res = await fetch('/api/conversations');
    const data = await res.json();
    if (!data.success) return;

    const listElem = document.getElementById('conversation-list');
    listElem.innerHTML = '';

    if (data.conversations.length === 0) {
      listElem.innerHTML = '<li style="color: #9ca3af; font-size: 0.8rem; padding: 10px;">No past consultations yet.</li>';
      return;
    }

    data.conversations.forEach(conv => {
      const li = document.createElement('li');
      li.className = 'conversation-item' + (conv.id === activeConversationId ? ' active' : '');
      li.dataset.id = conv.id;

      li.innerHTML = `
        <span class="conv-title" title="${escapeHtml(conv.title)}">💬 ${escapeHtml(conv.title)}</span>
        <button class="btn-delete-conv" title="Delete conversation" data-id="${conv.id}">🗑️</button>
      `;

      // Select conversation on click
      li.querySelector('.conv-title').addEventListener('click', () => {
        selectConversation(conv.id);
      });

      // Delete conversation handler
      li.querySelector('.btn-delete-conv').addEventListener('click', async (e) => {
        e.stopPropagation();
        if (confirm(`Delete consultation "${conv.title}"?`)) {
          await deleteConversation(conv.id);
        }
      });

      listElem.appendChild(li);
    });
  } catch (err) {
    console.error("Failed to load conversation list:", err);
  }
}

async function selectConversation(conversationId) {
  activeConversationId = conversationId;

  // Highlight active in sidebar
  document.querySelectorAll('.conversation-item').forEach(el => {
    el.classList.toggle('active', parseInt(el.dataset.id, 10) === conversationId);
  });

  try {
    const res = await fetch(`/api/conversations/${conversationId}`);
    const data = await res.json();
    if (!data.success) return;

    const chatWindow = document.getElementById('chat-window');
    chatWindow.innerHTML = '';

    if (data.messages.length === 0) {
      chatWindow.innerHTML = '<p style="color: #9ca3af; text-align: center; margin-top: 40px;">No messages in this conversation yet.</p>';
      return;
    }

    data.messages.forEach(msg => {
      renderMessage(msg.sender, msg.text, msg.image_filename, msg.is_simulated, msg.created_at);
    });

    scrollToBottom();
  } catch (err) {
    console.error("Failed to load conversation history:", err);
  }
}

async function deleteConversation(conversationId) {
  try {
    const res = await fetch(`/api/conversations/${conversationId}`, { method: 'DELETE' });
    const data = await res.json();
    if (data.success) {
      if (activeConversationId === conversationId) {
        startNewChat();
      }
      await loadConversations();
    }
  } catch (err) {
    alert("Failed to delete conversation: " + err.message);
  }
}

async function handleSendQuery() {
  const queryInput = document.getElementById('query-input');
  const sendBtn = document.getElementById('btn-send');
  const queryText = queryInput.value.trim();

  // Validate that user entered text OR staged an image
  if (!queryText && !stagedImageFile) {
    alert("Please enter a question or upload a plant photograph.");
    queryInput.focus();
    return;
  }

  // Hide welcome message if present
  const welcome = document.getElementById('empty-welcome');
  if (welcome) welcome.remove();

  // Render User Message immediately in UI
  const localImageSrc = stagedImageFile ? document.getElementById('staging-thumb').src : null;
  renderMessage('user', queryText || "[Uploaded crop photograph for diagnosis]", null, false, "Just now", localImageSrc);
  scrollToBottom();

  // Prepare FormData for multipart upload
  const formData = new FormData();
  if (queryText) formData.append('query', queryText);
  if (activeConversationId) formData.append('conversation_id', activeConversationId);
  if (stagedImageFile) formData.append('image', stagedImageFile);

  // Clear input fields and staging
  queryInput.value = '';
  queryInput.style.height = 'auto';
  clearStagedImage();

  // Disable send button while waiting
  sendBtn.disabled = true;

  // Render temporary "Thinking..." typing bubble
  const typingBubble = renderTypingIndicator();
  scrollToBottom();

  try {
    const response = await fetch('/api/query', {
      method: 'POST',
      body: formData
    });

    typingBubble.remove();

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new Error(errData.error || `Server returned error (${response.status})`);
    }

    const data = await response.json();

    if (!data.success) {
      throw new Error(data.error || "Advisory generation failed.");
    }

    // Update active conversation ID and refresh sidebar
    if (!activeConversationId && data.conversation_id) {
      activeConversationId = data.conversation_id;
      await loadConversations();
    }

    // Render Assistant Advisory Response
    const aiMsg = data.assistant_message;
    renderMessage('assistant', aiMsg.text, null, aiMsg.is_simulated, "Just now");
    scrollToBottom();

  } catch (error) {
    typingBubble.remove();
    console.error("Query Error:", error);
    renderErrorMessage(`Failed to receive response: ${error.message}. Please check your connection and try again.`);
    scrollToBottom();
  } finally {
    sendBtn.disabled = false;
  }
}

function renderMessage(sender, text, imageFilename = null, isSimulated = false, timestamp = "Just now", localImageSrc = null) {
  const chatWindow = document.getElementById('chat-window');
  const row = document.createElement('div');
  row.className = `message-row ${sender}`;

  const avatar = sender === 'user' ? '👨‍🌾' : '🌾';

  // Format message text with safe markdown converter
  const formattedHtml = formatMarkdown(text);

  let imageHtml = '';
  if (localImageSrc) {
    imageHtml = `<img src="${localImageSrc}" class="uploaded-preview-img" alt="Uploaded Crop Photo" onclick="window.open('${localImageSrc}')" />`;
  } else if (imageFilename) {
    const imgSrc = `/uploads/${encodeURIComponent(imageFilename)}`;
    imageHtml = `<img src="${imgSrc}" class="uploaded-preview-img" alt="Uploaded Crop Photo" onclick="window.open('${imgSrc}')" />`;
  }

  let simulationBadge = '';
  if (sender === 'assistant' && isSimulated) {
    simulationBadge = '<span class="weather-badge badge-simulated" style="margin-left: 6px;">Simulated Advisory</span>';
  }

  let speakButtonHtml = '';
  if (sender === 'assistant') {
    speakButtonHtml = `<button class="btn-speak" title="Listen aloud">🔊 Listen</button>`;
  }

  row.innerHTML = `
    <div class="message-avatar">${avatar}</div>
    <div class="message-bubble">
      ${imageHtml}
      <div class="message-text">${formattedHtml}</div>
      <div class="message-meta">
        <span>${timestamp} ${simulationBadge}</span>
        ${speakButtonHtml}
      </div>
    </div>
  `;

  // Attach speech handler if assistant message
  if (sender === 'assistant') {
    const speakBtn = row.querySelector('.btn-speak');
    if (speakBtn && voiceAssistant) {
      speakBtn.addEventListener('click', () => {
        voiceAssistant.speakText(text, speakBtn);
      });
    }
  }

  chatWindow.appendChild(row);
}

function renderTypingIndicator() {
  const chatWindow = document.getElementById('chat-window');
  const row = document.createElement('div');
  row.className = 'message-row assistant';
  row.id = 'typing-indicator-row';
  row.innerHTML = `
    <div class="message-avatar">🌾</div>
    <div class="message-bubble" style="color: #6b7280; font-style: italic;">
      Analyzing crop query and weather data...
    </div>
  `;
  chatWindow.appendChild(row);
  return row;
}

function renderErrorMessage(errorText) {
  const chatWindow = document.getElementById('chat-window');
  const row = document.createElement('div');
  row.className = 'message-row assistant';
  row.innerHTML = `
    <div class="message-avatar" style="background: #fee2e2;">⚠️</div>
    <div class="message-bubble" style="border-color: #fca5a5; background: #fff5f5; color: #b91c1c;">
      <strong>Notice:</strong> ${escapeHtml(errorText)}
    </div>
  `;
  chatWindow.appendChild(row);
}

function scrollToBottom() {
  const chatWindow = document.getElementById('chat-window');
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

/**
 * Beginner-Friendly Markdown Formatter:
 * Converts headings, bold text, lists, and line breaks into clean HTML.
 */
function formatMarkdown(text) {
  if (!text) return '';
  let safe = escapeHtml(text);

  // Bold (**text** or __text__)
  safe = safe.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

  // Headings (### Heading)
  safe = safe.replace(/^### (.*?)$/gm, '<h3>$1</h3>');
  safe = safe.replace(/^## (.*?)$/gm, '<h3 style="font-size: 1.1rem;">$1</h3>');

  // Unordered list items (- item or * item)
  safe = safe.replace(/^\s*[-*]\s+(.*?)$/gm, '<li>$1</li>');
  safe = safe.replace(/(<li>.*?<\/li>)/gs, '<ul>$1</ul>');

  // Clean up duplicate consecutive <ul> tags
  safe = safe.replace(/<\/ul>\s*<ul>/g, '');

  // Convert double linebreaks to paragraphs
  safe = safe.replace(/\n\n/g, '<br><br>');

  return safe;
}

function escapeHtml(string) {
  if (!string) return '';
  const map = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;'
  };
  return string.toString().replace(/[&<>"']/g, (m) => map[m]);
}

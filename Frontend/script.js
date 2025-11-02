const BACKEND_URL = 'https://meet-mind-multimodal-meeting-copilo.vercel.app/api';

document.addEventListener('DOMContentLoaded', () => {
    // =================================================================================
    // SECTION 1: NAVIGATION LOGIC
    // =================================================================================
    const navPreMeeting = document.getElementById('nav-pre-meeting');
    const navPostMeeting = document.getElementById('nav-post-meeting');
    const preMeetingSection = document.getElementById('pre-meeting-section');
    const postMeetingSection = document.getElementById('post-meeting-section');
    navPreMeeting.addEventListener('click', () => { navPreMeeting.classList.add('active'); navPostMeeting.classList.remove('active'); preMeetingSection.classList.remove('hidden'); postMeetingSection.classList.add('hidden'); });
    navPostMeeting.addEventListener('click', () => { navPostMeeting.classList.add('active'); navPreMeeting.classList.remove('active'); postMeetingSection.classList.remove('hidden'); preMeetingSection.classList.add('hidden'); });

    // =================================================================================
    // SECTION 2: PRE-MEETING SCHEDULER LOGIC
    // =================================================================================
    const scheduleBtn = document.getElementById('schedule-btn');
    const reminderTitleInput = document.getElementById('reminder-title');
    const reminderStartTimeInput = document.getElementById('reminder-start-time');
    const reminderEndTimeInput = document.getElementById('reminder-end-time');
    const reminderMessageInput = document.getElementById('reminder-message');
    const attendeeEmailsInput = document.getElementById('attendee-emails');
    const scheduleStatusContainer = document.getElementById('schedule-status-container');
    const meetingLinkContainer = document.getElementById('meeting-link-container');
    const meetingLinkOutput = document.getElementById('meeting-link-output');
    const copyLinkBtn = document.getElementById('copy-link-btn');

    const pollForMeetingLink = (meetingId) => {
        const interval = setInterval(async () => {
            try {
                const response = await fetch(`${BACKEND_URL}/get-meeting-link/${meetingId}`);
                if (response.ok) { const data = await response.json(); if (data.hangoutLink) { clearInterval(interval); scheduleStatusContainer.textContent = 'Success! Meeting scheduled and link received.'; meetingLinkOutput.value = data.hangoutLink; meetingLinkContainer.classList.remove('hidden'); } }
            } catch (error) { console.error("Polling error:", error); }
        }, 3000);
        setTimeout(() => clearInterval(interval), 60000);
    };

    scheduleBtn.addEventListener('click', async () => {
        const title = reminderTitleInput.value.trim();
        const startTime = reminderStartTimeInput.value;
        const endTime = reminderEndTimeInput.value;
        const message = reminderMessageInput.value.trim();
        const attendees = attendeeEmailsInput.value.trim().split(',').map(e => e.trim()).filter(e => e);
        if (!title || !startTime || !endTime || !message) { alert('Please fill out all fields in the Pre-Meeting section.'); return; }
        scheduleBtn.disabled = true; scheduleBtn.textContent = 'Scheduling...';
        scheduleStatusContainer.classList.add('hidden'); meetingLinkContainer.classList.add('hidden');
        try {
            const response = await fetch(`${BACKEND_URL}/schedule-reminder`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ title, startTime, endTime, message, attendees }) });
            const result = await response.json();
            if (!response.ok) throw new Error(result.detail);
            scheduleStatusContainer.textContent = result.message;
            scheduleStatusContainer.className = 'status-box status-success';
            scheduleStatusContainer.classList.remove('hidden');
            if (result.meetingId) pollForMeetingLink(result.meetingId);
        } catch (error) {
            scheduleStatusContainer.textContent = `Error: ${error.message}`;
            scheduleStatusContainer.className = 'status-box status-error';
            scheduleStatusContainer.classList.remove('hidden');
        } finally {
            scheduleBtn.disabled = false; scheduleBtn.textContent = 'Complete Setup & Schedule';
        }
    });

    copyLinkBtn.addEventListener('click', () => { meetingLinkOutput.select(); document.execCommand('copy'); copyLinkBtn.textContent = 'Copied!'; setTimeout(() => { copyLinkBtn.textContent = 'Copy'; }, 2000); });

    // =================================================================================
    // SECTION 3: POST-MEETING PROCESSING LOGIC
    // =================================================================================
    const processBtn = document.getElementById('process-btn');
    const audioFileInput = document.getElementById('audio-file-input');
    const fileLabel = document.getElementById('file-label');
    const progressContainer = document.getElementById('progress-container');
    const progressBarInner = document.getElementById('progress-bar-inner');
    const statusText = document.getElementById('status-text');
    const resultsContainer = document.getElementById('results-container');
    const summaryOutput = document.getElementById('summary-output');
    const transcriptOutput = document.getElementById('transcript-output');

    const fetchHistory = async () => {
        try {
            const response = await fetch(`${BACKEND_URL}/meetings`);
            if (!response.ok) throw new Error('Could not fetch history.');
            const meetings = await response.json();
            const historyList = document.getElementById('history-list');
            historyList.innerHTML = '';
            if (meetings.length === 0) { historyList.innerHTML = '<li>No recent meetings found.</li>'; return; }
            meetings.forEach(meeting => {
                const listItem = document.createElement('li');
                const date = new Date(meeting.upload_timestamp).toLocaleString();
                listItem.innerHTML = `<strong>${meeting.filename}</strong><span>Processed on: ${date}</span>`;
                listItem.addEventListener('click', () => { summaryOutput.innerText = meeting.summary; transcriptOutput.innerText = meeting.transcript; resultsContainer.classList.remove('hidden'); window.scrollTo({ top: 0, behavior: 'smooth' }); });
                historyList.appendChild(listItem);
            });
        } catch (error) {
            console.error('Failed to fetch history:', error);
            document.getElementById('history-list').innerHTML = '<li>Error loading history.</li>';
        }
    };

    audioFileInput.addEventListener('change', () => { fileLabel.textContent = audioFileInput.files.length > 0 ? audioFileInput.files[0].name : 'Choose an audio file...'; });

    processBtn.addEventListener('click', async () => {
        const file = audioFileInput.files[0];
        if (!file) { alert('Please select an audio file first.'); return; }

        processBtn.disabled = true;
        processBtn.style.display = 'none';
        resultsContainer.classList.add('hidden');
        progressContainer.classList.remove('hidden');
        progressBarInner.style.backgroundColor = '#3949ab';
        progressBarInner.style.width = '100%';
        statusText.textContent = 'Uploading & Processing... (This can take a minute)';
        
        const formData = new FormData();
        formData.append('file', file);
        
        try {
            const response = await fetch(`${BACKEND_URL}/transcribe-and-summarize`, {
                method: 'POST',
                body: formData,
            });

            const result = await response.json();
            if (!response.ok) {
                throw new Error(result.detail || 'An unknown error occurred during processing.');
            }
            summaryOutput.innerText = result.summary;
            transcriptOutput.innerText = result.transcript;
            resultsContainer.classList.remove('hidden');
            progressContainer.classList.add('hidden');
            fetchHistory();
        } catch (error) {
            console.error('An error occurred:', error);
            statusText.innerHTML = `<strong>Error:</strong> ${error.message}`;
            progressBarInner.style.backgroundColor = '#d9534f';
        } finally {
            processBtn.disabled = false;
            processBtn.style.display = 'block';
        }
    });

    // --- INITIALIZATION ---
    fetchHistory();
});

document.addEventListener('DOMContentLoaded', function() {
    // Exam Data (injected from template)
    const questions = window.examData.questions;
    const durationMinutes = window.examData.duration;
    const examId = window.examData.examId;
    const startTimeStr = window.examData.startTime; // If we want server-synced time
    
    let currentIndex = 0;
    const answers = {};
    let flags = 0;

    // Timer Logic
    // For simplicity, using client-side countdown based on duration
    let timeRemaining = durationMinutes * 60; 
    const timerDisplay = document.getElementById('timer-display');
    const timerBar = document.getElementById('timer-bar');
    
    function startTimer() {
        const totalTime = durationMinutes * 60;
        const interval = setInterval(() => {
            timeRemaining--;
            
            const minutes = Math.floor(timeRemaining / 60);
            const seconds = timeRemaining % 60;
            timerDisplay.textContent = `${minutes}:${seconds < 10 ? '0' : ''}${seconds}`;
            
            // Progress bar
            const percent = ((totalTime - timeRemaining) / totalTime) * 100;
            if(timerBar) timerBar.style.width = `${percent}%`;

            if (timeRemaining <= 0) {
                clearInterval(interval);
                alert("Time is up! Submitting exam.");
                submitExam();
            }
            
            // Warning at 5 mins
            if (timeRemaining === 300) {
                timerDisplay.classList.add('text-danger', 'animate__animated', 'animate__flash');
            }
        }, 1000);
    }

    // UI Rendering
    function renderQuestion(index) {
        if (index < 0 || index >= questions.length) return;
        currentIndex = index;
        
        const q = questions[index];
        const container = document.getElementById('question-container');
        
        // Animation out
        container.classList.remove('animate__fadeInRight');
        container.classList.add('animate__fadeOutLeft');
        
        setTimeout(() => {
            document.getElementById('q-number').textContent = `Question ${q.question_number} of ${questions.length}`;
            document.getElementById('q-text').textContent = q.question_text;
            
            const optionsContainer = document.getElementById('options-container');
            optionsContainer.innerHTML = '';
            
            q.options.forEach(opt => {
                const btn = document.createElement('div');
                btn.className = `option-card ${answers[q.id] === opt.option_text ? 'selected' : ''}`;
                btn.onclick = () => selectOption(q.id, opt.option_text);
                btn.innerHTML = `
                    <span class="opt-letter">${opt.option_letter}</span>
                    <span class="opt-text">${opt.option_text}</span>
                `;
                optionsContainer.appendChild(btn);
            });
            
            container.classList.remove('animate__fadeOutLeft');
            container.classList.add('animate__fadeInRight');
            
            updateNavigation();
            updatePalette();
        }, 300);
    }

    function selectOption(qId, optText) {
        answers[qId] = optText;
        // Update hidden input for form submission
        const hiddenInput = document.getElementById(`input_q_${qId}`);
        if(hiddenInput) hiddenInput.value = optText;
        
        renderQuestion(currentIndex); // Re-render to show selection state
    }

    function updateNavigation() {
        document.getElementById('btn-prev').disabled = currentIndex === 0;
        const nextBtn = document.getElementById('btn-next');
        if (currentIndex === questions.length - 1) {
            nextBtn.textContent = 'Finish';
            nextBtn.onclick = confirmSubmit;
            nextBtn.classList.remove('btn-primary');
            nextBtn.classList.add('btn-success');
        } else {
            nextBtn.textContent = 'Next';
            nextBtn.onclick = () => renderQuestion(currentIndex + 1);
            nextBtn.classList.add('btn-primary');
            nextBtn.classList.remove('btn-success');
        }
    }
    
    function updatePalette() {
        // Update sidebar palette
        questions.forEach((q, idx) => {
            const dot = document.getElementById(`palette-${idx}`);
            if (dot) {
                if(idx === currentIndex) dot.className = 'palette-item current';
                else if(answers[q.id]) dot.className = 'palette-item answered';
                else dot.className = 'palette-item';
            }
        });
    }

    function confirmSubmit() {
        if(confirm("Are you sure you want to submit?")) {
            submitExam();
        }
    }

    function submitExam() {
        document.getElementById('exam-form').submit();
    }

    // Proctoring
    document.addEventListener("visibilitychange", () => {
        if (document.hidden) {
            logEvent("TAB_SWITCH", "User switched tab or minimized window");
            alert("Warning: You are not allowed to switch tabs during the exam!");
            flags++;
        }
    });

    function logEvent(type, details) {
        fetch('/proctor/log', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                exam_id: examId,
                type: type,
                details: details
            })
        });
    }

    // Initialize
    startTimer();
    renderQuestion(0);
    
    // Bind Prev Button
    document.getElementById('btn-prev').onclick = () => renderQuestion(currentIndex - 1);
    
    // Microphone/Camera permissions logic would go here
     navigator.mediaDevices.getUserMedia({ audio: true, video: true })
        .then(stream => {
            console.log("Proctoring started: Camera access granted");
            // In a real app, stream this to a server or analyze periodically
        })
        .catch(err => {
            console.error("Proctoring error: ", err);
            alert("Camera access is required for proctoring. Please allow access.");
        });

});

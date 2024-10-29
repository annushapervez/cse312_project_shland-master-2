

function welcome() {
    document.addEventListener("keypress", function (event) {
        if (event.code === "Enter") {
            sendChat();
        }
    });

    updateQuizQuestions();
    console.log("yes");
    setInterval(updateQuizQuestions, 20000);
    //////////////////////////////////////////////////////////////////////////////////
    var socket = io.connect("http://localhost:8080/room");
    socket.on('connect', function() {
        console.log("User connected!");
    });

}
function updatePosts() {
    const request = new XMLHttpRequest();
    request.onreadystatechange = function () {
        if (this.readyState === 4 && this.status === 200) {
            clearPosts();
            const posts = JSON.parse(this.response);
            console.log(posts)
            for (const post of posts) {
                addPost(post);
            }
        }
    };
    request.open("GET", "/get-posts");
    request.send();
}

function updateQuizQuestions() {
    const request = new XMLHttpRequest();
    request.onreadystatechange = function () {
        if (this.readyState === 4 && this.status === 200) {
            clearQuiz();
            const questions = JSON.parse(this.response);
            console.log(questions)
            for (const question of questions) {
                addQuestion(question);
            }
        }
    };
    request.open("GET", "/get-quiz");
    request.send();
}

function clearQuiz() {
    const questions = document.getElementById('quiz-list');
    questions.innerHTML = '';
}

function addQuestion(question) {
    const questionList = document.getElementById('quiz-list');
    const questionItem = document.createElement('li');
    questionItem.innerHTML = `${question.username}: <strong>${question.title}</strong><br>${question.description}<br>`;
    questionList.appendChild(questionItem);

    if (question.image){
        const imageElement = document.createElement('img');
        //imageElement.alt = `Question Image`;
        imageElement.src = `/uploads/${question.image}`;
        imageElement.classList.add('question-image');
        questionItem.appendChild(imageElement);
    }

    const answerContainer = document.createElement('div');
    answerContainer.className = 'answer-container';

    for (let i = 0; i < question.choices.length; i++) {
        const answerLabel = document.createElement('label');
        answerLabel.setAttribute('for', `answer-${i}`);
        answerLabel.textContent = `${question.choices[i]}`;

        const answerInput = document.createElement('input');
        answerInput.type = 'radio';
        answerInput.name = `answer-${question._id}`;
        answerInput.id = `answer-${i}`;
        answerInput.value = i + 1;

        answerInput.style.marginLeft = '10px';
        answerContainer.appendChild(answerInput);
        answerContainer.appendChild(answerLabel);
    }

    answerContainer.style.marginLeft = '35px'
    questionList.appendChild(answerContainer);
    var questionID = question._id
    var submitButton = document.createElement('button');
    submitButton.innerHTML = 'submit answer';
    submitButton.name = 'submit-answer';
    submitButton.value = questionID;
    submitButton.style.marginLeft ='40px'
    questionList.appendChild(submitButton)

    // const sendQuestion;
    // var socketio = io();

    socketio.emit("message", question)

}


socketio.on("message", (data) =>{
    addQuestion(data);
    console.log('hey dude')
});

function welcome() {
    document.addEventListener("keypress", function (event) {
        if (event.code === "Enter") {
            sendChat();
        }
    });

    updatePosts();
    updateQuizQuestions();
    console.log("yes");
    setInterval(updatePosts, 20000);
    //////////////////////////////////////////////////////////////////////////////////
    // var socket = io.connect("http://localhost:8080");
    // socket.on('connect', function() {
    //     console.log("User connected!");
    // });

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

function clearPosts() {
    const postList = document.getElementById('post-list');
    postList.innerHTML = '';
}

function clearQuiz() {
    const questions = document.getElementById('quiz-list');
    questions.innerHTML = '';
}

function addPost(post) {
    const postList = document.getElementById('post-list');
    const postItem = document.createElement('li');
    postItem.innerText = `${post.username}: ${post.title} - ${post.description} - likes: ${post.likecount}`;
    postList.appendChild(postItem);

    var postID = post._id // record post id
    // var likeCount = post.likeCount;
    var likeButton = document.createElement('button'); // create like button
    likeButton.innerHTML = 'like post above';
    // likeButton.type = 'button'; // may not be necessary
    likeButton.name = 'like-button';
    likeButton.value = postID;
    // likeButton.onclick = likePost(likeButton);
    likeButton.addEventListener("click", function () {likePost(likeButton)});
    likeButton.style.marginLeft ='40px'
    postList.appendChild(likeButton) // append cb to li

    //var socketio = io();

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

    //const sendQuestion
    //var socketio = io();

    socketio.emit("message", question)

}

function likePost(likeButton) {
    const request = new XMLHttpRequest();
    request.open("POST", "/like-post");
    const postID = likeButton.value;
    const body = JSON.stringify({'_id': postID}); // is this enough? we valid them in the python file
    request.send(body);

    //var socketio = io();
}

socketio.on("message", (data) =>{
        addQuestion(data);
});

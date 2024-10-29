
// [
//     {
//         question: "Which is largest animal on the planet?",
//         answers: [
//             {text: "shark", correct: false},
//             {text: "blue whale", correct: true},
//             {text: "elephant", correct: false},
//             {text: "giraffe", correct: false},
//         ]
//     },
//     {
//         question: "Which is smallest continent in the world?",
//         answers: [
//             {text: "Asia", correct: false},
//             {text: "Australia", correct: true},
//             {text: "Arctic", correct: false},
//             {text: "Africa", correct: false},
//         ]
//     },
//     {
//         question: "Which is largest desert in the world",
//         answers: [
//             {text: "Kalahari", correct: false},
//             {text: "Gobi", correct: false},
//             {text: "Sahara", correct: false},
//             {text: "Antartica", correct: true},
//         ]
//     },
// ];

var questions;
function welcome() {

    generateQuestions();
    console.log("yes");
    // setInterval(updateQuizQuestions, 20000);
    var socket = io.connect("http://localhost:8080/room");
    socket.on('connect', function() {
        console.log("User connected!");
    });

}

function generateQuestions() {
    const request = new XMLHttpRequest();
    request.onreadystatechange = function () {
        if (this.readyState === 4 && this.status === 200) {
            questions = JSON.parse(this.response);
            console.log(questions)
            for (const question of questions) {
                showQuestion(question);
            }
        }
    };
    request.open("GET", "/get-userquiz");
    request.send();
}

const questionElement = document.getElementById("question");
const answerButtons = document.getElementById("answer-buttons");
const nextButton = document.getElementById("next-btn");

let currentQuestionIndex = 0;
let score = 0;

function startQuiz () {
    currentQuestionIndex = 0;
    score = 0;
    nextButton.innerHTML = 'Next';
    showQuestion();
}

function showQuestion() {
    resetState();
    let currentQuestion = questions[currentQuestionIndex];
    let questionNo = currentQuestionIndex + 1;
    questionElement.innerHTML = questionNo + '. ' + currentQuestion['question'];
    // console.log('yo')
    console.log(currentQuestion['question']);
    var i = 0;
    currentQuestion['answers'].forEach(answer => {
        console.log(i)
        const button = document.createElement('button');
        button.innerHTML = answer;
        button.value = i;
        button.type='submit';
        button.form='answer-question';
        button.classList.add('btn');
        answerButtons.appendChild(button);
        // if (answer.correct) {
        //     button.dataset.correct = answer.correct;
        // }
        button.addEventListener('click', selectAnswer);
        i = i + 1;
    });
}

function resetState() {
    nextButton.style.display = 'none';
    while(answerButtons.firstChild) {
        answerButtons.removeChild(answerButtons.firstChild);
    }
}

function answerQ(grade) {
    const request = new XMLHttpRequest();
    request.open("POST", "/answer-question");
    const title = questions[currentQuestionIndex]['question'];
    const desc = questions[currentQuestionIndex]['description'];
    const id = questions[currentQuestionIndex]['_id'];
    const answer = grade
    const body = JSON.stringify({'title': title, 'description': desc, 'grade': answer, '_id': id}); // is this enough? we valid them in the python file
    request.send(body);

}

function selectAnswer(e) {
    const selectedBtn = e.target.value;
    const correctAnswer = questions[currentQuestionIndex]['correct_answer'];

    console.log('selected button');
    console.log(selectedBtn);
    console.log('correct answer');
    console.log(correctAnswer);

    const isCorrect = Number(selectedBtn) === Number(correctAnswer);

    if (isCorrect) {
        console.log('correct');
        answerQ(1);
        score++;
    } else {
        console.log('incorrect');
        answerQ(0);
    }

    nextButton.style.display = 'block';

}

function showScore() {
    resetState();
    questionElement.innerHTML = `You scored ${score} out of ${questions.length}!`;
    nextButton.innerHTML = 'view gradebook'; // make a redirect
    nextButton.style.display = 'block';
}

function handleNextButton() {
    currentQuestionIndex++;
    if(currentQuestionIndex < questions.length) {
        showQuestion();
    } else {
        showScore();
    }
}

nextButton.addEventListener('click', () => {
    if(currentQuestionIndex < questions.length) {
        handleNextButton();
    } else {
        // redirect to score page or smthn instead of restarting the quiz
        const request = new XMLHttpRequest();
        window.location.href = "/grades";
        request.open("GET", "/grades");
        request.send();
    }
})

startQuiz();
function buyPlan(plan) {

    alert("Plan selected: " + plan);

    // future: payment gateway connect
    // fetch('/create-order', { method: 'POST' })

}

function startTimer() {
    let end = new Date();
    end.setHours(23,59,59,999); // daily reset

    function update() {
        let now = new Date();
        let diff = end - now;

        let h = Math.floor(diff / 1000 / 60 / 60);
        let m = Math.floor(diff / 1000 / 60) % 60;
        let s = Math.floor(diff / 1000) % 60;

        document.getElementById("timer").innerText =
            h + ":" + m + ":" + s;
    }

    setInterval(update, 1000);
}

startTimer();

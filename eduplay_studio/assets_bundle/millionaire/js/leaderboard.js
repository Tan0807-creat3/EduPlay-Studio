
// !IMPORTANT: REPLACE WITH YOUR OWN CONFIG OBJECT BELOW


// Initialize Firebase
var config = {
    apiKey: "AIzaSyBvHSH_oBAjtaXoZ6qLjtVtPMEGhYxIX20",
    authDomain: "wwbm-slvpkd.firebaseapp.com",
    databaseURL: "https://wwbm-slvpkd.firebaseio.com",
    projectId: "wwbm-slvpkd",
    storageBucket: "wwbm-slvpkd.appspot.com",
    messagingSenderId: "365633945854"
  };
  
  
  firebase.initializeApp(config);
  
  // Firebase Database Reference and the child
  const dbRef = firebase.database().ref();
  const usersRef = dbRef.child('leaderboard');
  let v1 = false;
  
  
  readUserData();
  mainLeaderboard();
  
  // Validation
  var nameInput = $('#name');
  if (nameInput.length) {
    nameInput.on('input', function() {
      var input = $('#name').val();
      if (input.length > 0) {
        $('#addToLeaderboardBtn').fadeIn();
        $('#scoreBtn').fadeIn();
      } else {
        $('#addToLeaderboardBtn').fadeOut();
        $('#scoreBtn').fadeOut();
      }
    });
  }
  
  
  
  // --------------------------
  // READ
  // --------------------------
  function readUserData() {
  
    const leaderboard = document.getElementById("leaderboard_data");
    if (!leaderboard) {
      return;
    }
  
    usersRef.orderByChild('score').on("value", snap => {
      const data = [];
      leaderboard.innerHTML = ""
  
  
      var table = document.createElement("table");
      table.className = "table table-striped table-responsive table-bordered table-dark table-fixed";
      var thead = document.createElement("thead");
      thead.className = "thead-light";
      var tbody = document.createElement("tbody");
      tbody.className = "tbody-light";
  
      //TABLE HEADER
      var headRow = document.createElement("tr");
       var th1 = document.createElement("th"); 
       th1.className = "col-2 text-center";
       th1.appendChild(document.createTextNode("Rank"));
       
       var th2 = document.createElement("th");
       th2.className = "col-8";
       th2.appendChild(document.createTextNode("Name"));

       var th3 = document.createElement("th");
       th3.className = "col-2";
       th3.appendChild(document.createTextNode("Score"));
    
       headRow.appendChild(th1);
       headRow.appendChild(th2);
       headRow.appendChild(th3);
    
      thead.appendChild(headRow);
      table.appendChild(thead);
  
      snap.forEach(childSnap => {
  
        let key = childSnap.key,
          value = childSnap.val();
  
        const scoreData = parseInt(value.score);
        const dataObj = {
  
          name: value.name,
          score: scoreData
        }
  
        data.push(dataObj);
      });
  
      data.sort(function(a, b) {
        return b.score - a.score
      });
  
      for (i = 0; i < data.length; i++) {
        var tr = document.createElement("TR");
        tr.setAttribute("id", i);
  
        var z0 = document.createElement("TD");
        z0.className = "col-2 text-center";
        var t0 = document.createTextNode(i + 1);
  
        var z1 = document.createElement("TD");
        z1.className = "col-8";
        var t1 = document.createTextNode(data[i].name);
  
        var z2 = document.createElement("TD");
        z2.className = "col-2";
        var t2 = document.createTextNode(data[i].score);
  
         z0.appendChild(t0);
        z1.appendChild(t1);
        z2.appendChild(t2);
        tr.appendChild(z0);
        tr.appendChild(z1);
        tr.appendChild(z2);  
              tbody.appendChild(tr);
      }
  
      table.appendChild(tbody);
      leaderboard.append(table);
  
    });
  
  }
  
  // --------------------------
  // ADD
  // --------------------------
  
  var scoreBtn = document.getElementById("scoreBtn");
  if (scoreBtn) {
    scoreBtn.addEventListener("click", addUserScore);
  }
  
  var exitGameBtn = document.getElementById("exitGameBtn");
  if (exitGameBtn) {
    exitGameBtn.addEventListener("click", function() {
      $('#gameWindow').fadeOut(500);
      setTimeout(function(){
        if (typeof window.resetToHome === 'function') {
          window.resetToHome();
        } else {
          location.reload();
        }
      }, 600);
    });
  }
  
  
  function addUserScore() {
    if (!$('#name').length) {
      return;
    }

    const usersRef = dbRef.child('leaderboard');
    let userScore = {};
    userScore.name = $('#name').val();
    userScore.score = finalScore;
    usersRef.push(userScore);
  
 
    $('#gameWindow').fadeOut(1000);
    

    setTimeout($.proxy(function () {
        location.reload();
    }, this), 4000);
  
  }
  


    // --------------------------
  // READ
  // --------------------------
  function mainLeaderboard() {
  
    const leaderboard = document.getElementById("leaderboardMain_data");
  
    usersRef.orderByChild('score').on("value", snap => {
      const data = [];
      leaderboard.innerHTML = ""
  
  
      var table = document.createElement("table");
      table.className = "table table-striped table-responsive table-sm table-bordered table-dark table-fixed";
      var thead = document.createElement("thead");
      thead.className = "thead-light";
      var tbody = document.createElement("tbody");
      tbody.className = "tbody-light";
  
      //TABLE HEADER
      var headRow = document.createElement("tr");
       var th1 = document.createElement("th"); 
       th1.className = "col-2 text-center";
       th1.appendChild(document.createTextNode("Rank"));
       
       var th2 = document.createElement("th");
       th2.className = "col-6";
       th2.appendChild(document.createTextNode("Name"));

       var th3 = document.createElement("th");
       th3.className = "col-4";
       th3.appendChild(document.createTextNode("Score"));
    
       headRow.appendChild(th1);
       headRow.appendChild(th2);
       headRow.appendChild(th3);
    
      thead.appendChild(headRow);
      table.appendChild(thead);
  
      snap.forEach(childSnap => {
  
        let key = childSnap.key,
          value = childSnap.val();
  
        const scoreData = parseInt(value.score);
        const dataObj = {
  
          name: value.name,
          score: scoreData
        }
  
        data.push(dataObj);
      });
  
      data.sort(function(a, b) {
        return b.score - a.score
      });
  
      for (i = 0; i < data.length; i++) {
        var tr = document.createElement("TR");
        tr.setAttribute("id", i);
  
        var z0 = document.createElement("TD");
        z0.className = "col-2 text-center";
        var t0 = document.createTextNode(i + 1);
  
        var z1 = document.createElement("TD");
        z1.className = "col-6";
        var t1 = document.createTextNode(data[i].name);
  
        var z2 = document.createElement("TD");
        z2.className = "col-4";
        var t2 = document.createTextNode(data[i].score);
  
         z0.appendChild(t0);
        z1.appendChild(t1);
        z2.appendChild(t2);
        tr.appendChild(z0);
        tr.appendChild(z1);
        tr.appendChild(z2);  
              tbody.appendChild(tr);
      }
  
      table.appendChild(tbody);
      leaderboard.append(table);
  
    });
  
  }

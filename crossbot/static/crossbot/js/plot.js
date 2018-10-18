// Globals
const TIME_MODEL_NAME_MAP = {
  'minicrossword': "Mini Crossword",
  'crossword': "Crossword",
  'easysudoku': "Easy Sudoku",
}

//adapted from https://stackoverflow.com/questions/48719873/how-to-get-median-and-quartiles-percentiles-of-an-array-in-javascript-or-php
//adapted from https://blog.poettner.de/2011/06/09/simple-statistics-with-php/
Array.prototype.quartile = function(q) {
  var data = this.slice();
  data.sort(); // TODO: fix sorting here and everywhere else, use function
  var pos = ((data.length) - 1) * q;
  var base = Math.floor(pos);
  var rest = pos - base;
  if( (data[base+1]!==undefined) ) {
    return data[base] + rest * (data[base+1] - data[base]);
  } else {
    return data[base];
  }
}

Array.prototype.quartile_75 = function() {
  return this.quartile(0.75);
}
Array.prototype.quartile_50 = function() {
  return this.quartile(0.50);
}
Array.prototype.quartile_25 = function() {
  return this.quartile(0.25);
}
Array.prototype.median = function() {
  return this.quartile_50();
}

Array.prototype.sum = function() {
   return this.reduce(function(a, b) { return a + b; }, 0);
}

Array.prototype.average = function() {
  if (this.length == 0) {
    return 0;
  }
  return this.sum() / this.length;
}

Array.prototype.stdev = function() {
   var mean = this.average();
   return Math.sqrt(this.map(x => Math.pow(x - mean, 2)).average());
}

// function setDefaultDates() {
//   var d = new Date();

//   function toVal(date) {
//     return date.toISOString().split('T')[0];
//   }

//   $('#plot-settings input[name="end-date"]').val(toVal(d));
//   d.setDate(d.getDate() - 10);
//   $('#plot-settings input[name="start-date"]').val(toVal(d));
// }

function plotData(data) {
  var times = data.times;

  // Normalize the data if necessary
  if($('#plot-settings input[name="plot-mode"][value="normalized"]').is(':checked')) {
    times = normalizeTimes(data.times);
  }

  const today = new Date();
  const one_week_ago = new Date(today);
  one_week_ago.setDate(one_week_ago.getDate() - 7);
  var end = data['end'];
  if (new Date(end) > today) {
    end = today;
  }

  // First, compile the times into user data
  var userDataMap = {};
  window.userDataMap = userDataMap;
  for (var time of times) {
    // Discard future times
    if (new Date(time.date) > new Date(end)) {
      continue;
    }

    if (!(time.user in userDataMap)) {
      userDataMap[time.user] = {
        type: 'scattergl',
        name: time.user,
        mode: 'lines+markers',
        connectgaps: false,
        x: [],
        y: [],
      }
    } else {
      // Push enough nulls to bring us up to date
      // TODO: I think this breaks on DST (Mar 11)
      var u = userDataMap[time.user];
      var prev = new Date(u.x[u.x.length - 1]);
      prev.setDate(prev.getDate() + 1)
      var next = new Date(time.date);
      if (prev < next) {
        u.x.push(null);
        u.y.push(null);
      }
    }
    var u = userDataMap[time.user];
    u.x.push(time.date);
    u.y.push(time.seconds);
  }

  var userData = [];
  window.userData = userData;
  for (var user in userDataMap) {
    userData.push(userDataMap[user]);
  }



  var layout = {
    title: TIME_MODEL_NAME_MAP[data['timemodel']],
    xaxis: {
      title: 'Date',
      range: [one_week_ago, today],
      type: 'date',
      zeroline: false,
      fixedrange: true,
      rangeselector: {buttons: [
        {
          count: 7,
          label: '1w',
          step: 'day',
          stepmode: 'backward'
        },
        {
          count: 1,
          label: '1m',
          step: 'month',
          stepmode: 'backward'
        },
        {
          count: 1,
          label: '1y',
          step: 'year',
          stepmode: 'backward'
        }
      ]},
      rangeslider: {range: [data['start'], today]},
      type: 'date'
    },
    yaxis: {
      title: 'Time (s)',
      autorange: true,
      fixedrange: true,
    },
    showlegend: true,
  };

  Plotly.newPlot('chart', userData, layout);
}


function normalizeTimes(times) {
  const timesByDate = {};
  for (var time of times) {
    if (!(time.date in timesByDate)) {
      timesByDate[time.date] = {};
    }
    timesByDate[time.date][time.user] = time.seconds;
  }

  const sortedDates = Object.keys(timesByDate).sort();

  const MAX_SCORE = 1.5;
  const FAILURE_PENALTY = -2

  function mkScore(mean, t, stdev) {
    if (t < 0) {
      return FAILURE_PENALTY;
    }
    if (stdev == 0) {
      return 0;
    }

    var score = (mean - t) / stdev;
    if (score < -MAX_SCORE) {
      return -MAX_SCORE;
    }
    if (score > MAX_SCORE) {
      return MAX_SCORE;
    }
    return score;
  }

  var scoresForDate = {};
  for (var date in timesByDate) {
    var times = Object.values(timesByDate[date]);
    var worstTime = Math.max(...times);

    // make failures 1 minute worse than the worst time
    times = times.map(function(t) {
      if (t >= 0) {
        return t;
      } else {
        return worstTime + 60;
      }
    });

    var q1 = times.quartile_25();
    var q3 = times.quartile_75();
    var stdev = times.stdev();
    var o1 = q1 - stdev;
    var o3 = q3 - stdev;

    times = times.filter(t => t >= o1 && t <= o3);
    var mean = times.average();
    var stdev = times.stdev();

    scoresForDate[date] = {};
    for (user in timesByDate[date]) {
      scoresForDate[date][user] = mkScore(mean, timesByDate[date][user], stdev);
    }
  }

  const NEW_SCORE_WEIGHT = 1 - $('#plot-settings input[name="smoothing-factor"]').val();
  const running = {};
  const weightedScores = []; // simple list of objects

  for (var date of sortedDates) {
    for (var user in scoresForDate[date]) {
      var score = scoresForDate[date][user];

      var oldScore = score;
      if (user in running) {
        oldScore = running[user];
      }

      var newScore = score * NEW_SCORE_WEIGHT + oldScore * (1 - NEW_SCORE_WEIGHT);
      running[user] = newScore;

      weightedScores.push({
        user: user,
        date: date,
        seconds: newScore,
      });
    }
  }

  return weightedScores;
}

function getData() {
  var url = '/rest-api/times/'

  var timeModel = $('#plot-settings input[name="time-model"]:checked').val();
  if (timeModel != undefined) {
    url += timeModel + '/';
  }

  $.get(url, plotData);
}

$(function() {
  getData();
  $("#plot-settings").on("change", ":input", function() {
    getData();
  });
});

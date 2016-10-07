
$(document).on('ready', function(){
    if (!epochs) {
	throw new Error("Error while loading model");
    }
    // load from database epochs (perhaps better as ajax?)
    var columns = [];
    var byTag = {};
    for (var idx in epochs) {
	for (var key in epochs[idx]) {
            if(!byTag.hasOwnProperty(key)){
		byTag[key] = [epochs[idx][key]];
            } else {
		byTag[key][idx] = epochs[idx][key];
            }
	}
    }
    for (var key in byTag){
	columns.push([key].concat(byTag[key]));
    }
    var chart = c3.generate({
	bindto:'#chart',
	data: {
	    columns: columns
	}
    });
    
    // epoch event source
    var epochSource = new EventSource('/subscribe/epoch/end/');
    epochSource.onopen = function() {
	console.log('Connected to /subscribe/epoch/end/');
    };
    epochSource.onerror = function(e) {
	console.log("Couldn't subscribe to /subscribe/epoch/end/");
    };
    epochSource.addEventListener('epoch', function(e) {
	var data  = JSON.parse(e.data);
	if (!data.hasOwnProperty('modelId')) {
	    throw new Error('Received event without target');
	}
	if (!chart){
	    throw new Error('Expected existing chart');
	}
	if (data.modelId === modelId.toString()) { // check target
	    for (var key in data.epochData) {
		if(byTag.hasOwnProperty(key)) {
		    byTag[key].push(data.epochData[key]);
		}
	    }
	    var columns = [];
	    for (var key in byTag){
		columns.push([key].concat(byTag[key]));
	    }
	    chart.load({
		columns: columns
	    });
	}
    });
});

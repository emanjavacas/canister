
$(document).on('ready', function(){
    var columns = [];
    var byTag = {};
    for (var idx in epochs) {
	for (var key in epochs[idx]) {
            if(! byTag.hasOwnProperty(key)){
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
	data: {
	    bindto:'#chart',
	    columns: columns
	}
    });
});


$(document).on('ready', function() {
    toastr.options = {
	positionClass: 'toast-bottom-right',
	timeOut: 10000
    };
    // train event source
    var trainSource = new EventSource('/subscribe/train/');
    trainSource.onopen = function() {
	console.log('Connected to /subscribe/epoch/end/');
    };
    trainSource.onerror = function(e) {
	console.log("Couldn't subscribe to /subscribe/epoch/end/");
    };
    trainSource.addEventListener('train', function(e) {
	var data = JSON.parse(e.data);
	console.log("publish/train/: " + data);
	var msg = data.action === 'start'? 'Started' : 'Finished' +
	    ' training for model ' + data.modelId;
	toastr.info(msg, {timeOut: 5000});
    });

    $('[data-toggle="tooltip"]').tooltip(); // info tooltip

    $('a').on('click', function(e) { // handle tag-remove/add
	var tag = $(e.target).data('tag');
	var action = $(e.target).data('action');
	console.log(tag);
	$.ajax({
	    type: "POST",
	    url: "/tags",
	    data: {"tag": tag, "action": action}
	}).done(function(data){
	    console.log(data);
	    window.location.replace(data.endpoint);
	}).fail(function(){
	    console.log("Error!");
	});
    });
});

if (typeof lyra == "undefined") { lyra = {}; }

lyra.main = function() { this.initialize.apply(this, arguments) }
lyra.main.prototype = {
    initialize: function() {
	var that = this;
	$(".event").click(function(e) { that.onClick(e, this) });
    },
    onClick: function(evt, element) {
	var $el = $(element);
	var wasTop = $el.hasClass("topmost");
	var wasBottom = $el.hasClass("bottommost");
	$(".event").each(function() { 
	    $(this).removeClass("topmost");
	    $(this).removeClass("bottommost");
	});
	if (wasTop) {
	    $el.addClass("bottommost");
	} else if (!wasBottom) {
	    $el.addClass("topmost");
	}
    }
};

var lyra_inst = new lyra.main();
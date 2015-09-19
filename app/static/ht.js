BASE_URL="http://localhost:5000/api/v1.0/";

var Module = Backbone.Model.extend({});

var ModulesCollection = Backbone.Collection.extend({
	defaults: {
		model: Module,
	},
	model: Module,
	url: BASE_URL + "modules/list",
});


var AppView = Backbone.View.extend({
	el: '#container',
	initialize: function(){
		var self = this;
		this.mlist = new ModulesCollection();
		this.mlist.fetch().done(function(){
			return self.render();
		});
	},
		

	render: function(){
		return $.ajax({
			type: "POST",
			url: BASE_URL + "module/0/set", 
			contentType:"application/json; charset=utf-8",
			dataType:"json",
			data: JSON.stringify({ "graph": true, "result_type": "test" }),
			success: function(data) {
				alert(data);
				}
			});
			// console.log(this.mlist.at(i).get('options'));
		
	}

});


var appView = new AppView();


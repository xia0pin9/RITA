BASE_URL="http://localhost:5000/api/v1.0/";

var Module = Backbone.Model.extend({});
var ModuleOption = Backbone.Model.extend({});

var OptionsList = Backbone.Collection.extend({
	model: ModuleOption
});
var ModulesCollection = Backbone.Collection.extend({
	model: Module,

	url: BASE_URL + "modules/list",
});

/*************************************
       View for Module Collection
*************************************/
var ModuleListView = Backbone.View.extend({
  initialize: function(){
    var self = this;
    this.mlist = new ModulesCollection();
    this.mlist.fetch().done(function(){
      return self.render();
    });
  },
  render: function() {
    var appStr = '<tbody>';
    for(var i =0; i < this.mlist.length;i++)
    {
      //create new table row for each module
      var mod = this.mlist.at(i);
      mname = mod.get('name');
      mname = mname[0].toUpperCase()+mname.slice(1);
      appStr += '<tr class="options-row"><th class="options-head"><h2>' + mname + '</h2><h4>' + mod.get('description') + '</h4></th>';
      var olv = ( new OptionListView ({collection: mod.get('options'), id: i, el: '.options'}));
      appStr += olv.render();
      appStr += '</tr>';
    }
    appStr += '</tbody>';
    $(this.el).append(appStr);      
  }
});

/*************************************
       View for Options Collection
*************************************/
var OptionListView = Backbone.View.extend({
	collection: OptionsList,
	initialize: function(){
		this.list = new OptionsList();
		this.list.set(this.collection);
	},
	render: function() {
    var appStr = '<td class="options">';
		for(var j=0; j < this.list.length; j++)
    {
      //create two columns of options
      if(j == Math.ceil(this.list.length/2))
        appStr += '</td><td class="options">';
    	var mov = new ModuleOptionView({model: this.list.at(j), id: this.id, el: '.options'});
    	appStr += mov.render();
      if(this.list.length == 1)
        appStr +='</td><td class="options">';
		}
    appStr +='</td><td class="runBtn"><button onclick="moduleRun('+this.id+')">Run Module</button><img id="run-img'+this.id+'" src="img/loader.gif" class="loader"/></td>';
    return appStr;
  }
});


/*************************************
    View for a Single ModuleOption
*************************************/
var ModuleOptionView = Backbone.View.extend({  
  render: function() {
    var type = (this.model.get('type'))
    var appStr = "";
    //use option type to determine input type and format label placement
    if (type === "bool")
      appStr += "<div class='option-div'><label class='label-option'>"+this.model.get('name')+"</label>  <input class='boolInput input-option' id='"+this.id+"' type='checkbox' name='"+this.model.get('name')+"' checked='"+this.model.get('value')+"' onchange='moduleOptionChanged(this.name, this.checked, this.id)'/></div>";
    else if (type === "string")
      appStr += "<div class='option-div'><h5 class='label-option'> <label class='label-option'>"+this.model.get('name')+"</label></h5><input class='stringInput input-option' id='"+this.id+"' type='text' name='"+this.model.get('name')+"' value='"+this.model.get('value')+"' onchange='moduleOptionChanged(this.name, this.value, this.id)'/></div>";
    else
      appStr += "<div class='option-div'><label class='label-option'>"+this.model.get('name')+"</label>  <input class='numberInput input-option' id='"+this.id+"' type='number' name='"+this.model.get('name')+"' value='"+this.model.get('value')+"' onchange='moduleOptionChanged(this.name, this.value, this.id)'/></div>";
    return appStr;
  }
});

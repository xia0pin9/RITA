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
      var mod = this.mlist.at(i);
      mname = mod.get('name');
      mname = mname[0].toUpperCase()+mname.slice(1);
      appStr += '<tr class="module-row"><th class="module-head"><h2>' + mname + '</h2><h4>' + mod.get('description') + '</h4></th>';
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
    var appStr = '<td class="module-options">';
		for(var j=0; j < this.list.length; j++)
    {
      if(j == this.list.length/2)
        appStr += '</td><td class="module-options">';
    	var mov = new ModuleOptionView({model: this.list.at(j), id: this.id, el: '.options'});
    	appStr += mov.render();
      if(this.list.length == 1)
        appStr +='</td><td>';
		}
    appStr +='</td><td class="runBtn"><button class="active" onclick="moduleRun('+this.id+')">Run Module</button><img id="run-img'+this.id+'" src="img/loader.gif" class="deactive"/></td>';
    return appStr;
  }
});


/*************************************
    View for a Single ModuleOption
*************************************/
var ModuleOptionView = Backbone.View.extend({  
  render: function() {
    var type = (this.model.get('type'))
    if (type === "bool"){
      var appStr = "<label>"+this.model.get('name')+"</label>  <input class='"+this.model.get('name')+"' id='"+this.id+"' type='checkbox' name='"+this.model.get('name')+"' checked='"+this.model.get('value')+"' onchange='fieldChanged(this.name, this.checked, this.id)'/></br>";
      return appStr;
    }
    else if (type === "string")
        type = "text";              
    else
        type = "number";  
    var appStr = "<label>"+this.model.get('name')+"</label>  <input class='"+this.model.get('name')+"' id='"+this.id+"' type='"+type+"' name='"+this.model.get('name')+"' value='"+this.model.get('value')+"' onchange='fieldChanged(this.name, this.value, this.id)'/></br>";
    return appStr;
  }
});

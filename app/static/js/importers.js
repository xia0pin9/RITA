BASE_URL="http://localhost:5000/api/v1.0/";

var Importer = Backbone.Model.extend({});
var ImporterOption = Backbone.Model.extend({});

var ImporterOptionsList = Backbone.Collection.extend({
  model: ImporterOption
});
var ImportersCollection = Backbone.Collection.extend({
  model: Importer,

  url: BASE_URL + "importers/list",
});

/*************************************
       View for Importer Collection
*************************************/
var ImporterListView = Backbone.View.extend({
  initialize: function(){
    var self = this;
    this.list = new ImportersCollection();
    this.list.fetch().done(function(){
      return self.render();
    });
  },
  render: function() {
    var appStr = '<tbody>';
    for(var i =0; i < this.list.length;i++)
    {
      //create new table row for each module      
      var imp = this.list.at(i);
      name = imp.get('name');
      name = name[0].toUpperCase()+name.slice(1);
      appStr += '<tr class="options-row"><th class="options-head"><h2>' + name + '</h2><h4>' + imp.get('description') + '</h4></th>';
      var iolv = ( new ImporterOptionListView ({collection: imp.get('options'), id: i, el: '.options'}));
      appStr += iolv.render();
      appStr += '</tr>';
    }
    appStr += '</tbody>';
    $(this.el).append(appStr);      
  }
});

/*************************************
       View for Options Collection
*************************************/
var ImporterOptionListView = Backbone.View.extend({
  collection: ImporterOptionsList,
  initialize: function(){
    this.list = new ImporterOptionsList();
    this.list.set(this.collection);
  },
  render: function() {
    var appStr = '<td class="options">';
    for(var j=0; j < this.list.length; j++)
    {
      //create two columns of options
      if(j == Math.ceil(this.list.length/2))
        appStr += '</td><td class="options">';
      var iov = new ImporterOptionView({model: this.list.at(j), id: this.id, el: '.options'});
      appStr += iov.render();
      if(this.list.length == 1)
        appStr +='</td><td>';
    }
    appStr +='</td><td class="runBtn"><button onclick="importerRun('+this.id+')">Import</button><img id="importrun-img'+this.id+'" src="img/loader.gif" class="loader"/></td>';
    return appStr;
  }
});


/*************************************
    View for a Single Importer Option
*************************************/
var ImporterOptionView = Backbone.View.extend({  
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

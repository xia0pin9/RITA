  BASE_URL="http://localhost:5000/api/v1.0/";
  var Importer = Backbone.Model.extend({});
  var ImporterOption = Backbone.Model.extend({});

  var ImporterOptionsList = Backbone.Collection.extend({
    model: ImporterOption
  });
  var ImporterCollection = Backbone.Collection.extend({
    model: Importer,

    url: BASE_URL + "importers/list",
  });

  /*************************************
      View for Single Importer Option
  *************************************/
  var ImporterOptionView = Backbone.View.extend({  
    render: function() {
        var appStr = "<label>Importer Option</label></br>";
      return appStr;
    }
  });

  /*************************************
      View for Importer Options Collection
  *************************************/
  var ImporterOptionListView = Backbone.View.extend({
    collection: ImporterOptionsList,
    initialize: function(){
      this.list = new ImporterOptionsList();
      this.list.set(this.collection);
    },
    render: function() {
      var appStr = "<form class='options'>";
      for(var j=0; j < this.list.length; j++)
      {
        var ImpOptView = new ImporterOptionView({model: this.list.at(j), el: '.options'});
        appStr += ImpOptView.render();
      }
      appStr +="</form>";
      return appStr;
    }
  });

  /*************************************
         View for Import Collection
  *************************************/
  var ImporterListView = Backbone.View.extend({
    initialize: function(){
      var self = this;
      this.ilist = new ImporterCollection();
      this.ilist.fetch().done(function(){
        return self.render();
      });
    },
    render: function() {
      for(var i =0; i < this.ilist.length;i++)
      {
        var imp = this.ilist.at(i);
        $(this.el).append('<h2>Import Name</h2>');
        $(this.el).append('<h4>Import Description</h4>');
        var ImpOptLiView = ( new ImporterOptionListView ({collection: imp.get('options'), el: '.options'}));
        $(this.el).append(ImpOptLiView.render());
      }
    }
  });
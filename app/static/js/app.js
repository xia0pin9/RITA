var myApp = myApp || {};
$.getScript("modules.js", function(){});
$.getScript("importers.js", function(){});

$(function () {

/***********************
Tab Views
***********************/
var TabsView = Backbone.View.extend({
  $label     : $("#tabs").find("ul"),
  $content   : $("#tabs").find("div"),
  tabs       : [
		{label : "Modules", content : '<div class="row"><table class="module"><thead><tr><h1 class="header">Modules</h1></tr></thead></table></div>', active : true},
    {label : "Import", content : '<div class="row"><div class="import body col-offset-md-3 col-md-6"><h1 class="header">Logs to Import</h1></div></div>', active : false},
    {label : "Settings", content : '<div class="row"><div class="settings body col-offset-md-3 col-md-6"><h1 class="header">Settings</h1></div></div>', active : false},
    {label : "Results", content : '<div class="row"><div class="results body col-offset-md-3 col-md-6"><h1 class="header">Results</h1></div></div>', active : false}
  ],
  labelTmpl       : _.template($("#label-tmpl").html()),
  contentTmpl       : _.template($("#content-tmpl").html()),
  initialize : function () {
    this.render();
    this.setState();
  },
  render     : function () {
    var labelHtml = "";
    var contentHtml = "";
    _.each(this.tabs, function (tab) {
        labelHtml += this.labelTmpl(tab).trim();
      contentHtml += this.contentTmpl(tab).trim();
    }, this);
    this.$label.html(labelHtml);
    this.$content.html(contentHtml);
  },
  setState   : function () {
    var Events = {
      bind    : function () {
        if (!this.o) this.o = $({});
        this.o.on.apply(this.o, arguments);
      },
      trigger : function () {
        if (!this.o) this.o = $({});
        this.o.trigger.apply(this.o, arguments);
      }
    };
    //StateMachine
    var SM = function () {
    };
    SM.fn = SM.prototype;
    $.extend(SM.fn, Events);
    SM.fn.add = function (tab) {
      this.bind("change", function (e, current) {
        if (tab === current) {
          tab.activate();
        }else {
          tab.deactivate();
        }
      });
      tab.changeState = $.proxy(function () {
        this.trigger("change", tab);
      }, this);
    };
    var sm = new SM;
    this.$label.find("li").each(function () {
      $(this).click(function(){
        if(!$(this).hasClass("active")){
          this.changeState();
        }
      });
      this.activate = function(){
        var self = this;
        $(self).addClass("active");
        $("#content-" + $(self).data("label")).removeClass("deactive");
      };
      this.deactivate = function(){
        var self = this;
        $(self).removeClass("active");
        $("#content-" + $(self).data("label")).addClass("deactive");
      };

      sm.add(this);
    });
  }
});


	var tabView = new TabsView({el: "#tabs"});
	var importView = new ImporterListView({el: '.import'});
	var moduleView = new ModuleListView({el: '.module'});

});

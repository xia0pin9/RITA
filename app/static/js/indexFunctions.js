/**************************************************
*Accept option field name, value and module id
*Update module option with new value on server
**************************************************/
function moduleOptionChanged (field, value, id){
  var updateField = "{\""+field+"\":\""+value+"\"}";
  return $.ajax({
    type: "POST",
    url: BASE_URL + "module/"+id+"/set", 
    contentType:"application/json; charset=utf-8",
    dataType:"json",
    data: updateField,
    success: function(){console.log("Module option "+field+" for Module "+id+" updated");},
    error: function(){console.log("Unable to update module option "+field+" for Module "+id);}
  });
}

/**************************************************
*Accept option field name, value and import log id
*Update import log option with new value on server
**************************************************/
function importOptionChanged (field, value, id){
  var updateField = "{\""+field+"\":\""+value+"\"}";
  return $.ajax({
    type: "POST",
    url: BASE_URL + "importer/"+id+"/set", 
    contentType:"application/json; charset=utf-8",
    dataType:"json",
    data: updateField,
    success: function(){console.log("Import log option "+field+" for import log "+id+" updated");},
    error: function(){console.log("Unable to update import log option "+field+" for import log "+id);}
  });
}


/**************************************************
*Run specific module inicated by id
*Disable all buttons while module is running
*Display loading gif for module indicated by id
**************************************************/
function moduleRun (id){
  var image = "run-img"+id;
  var buttons = document.getElementsByTagName('button');
  //hide no results view and replace with process results view
  document.getElementById("no-results").style.display = 'none';
  document.getElementById("process-results").style.display = 'block';  
  //display loader gif
  document.getElementById(image).style.display = 'block';
  //hide page buttons
  for(var i=0; i< buttons.length; i++)
    buttons[i].style.display = 'none';
  
  return $.ajax({
    type: "GET",
    url: BASE_URL + "module/"+id+"/run", 
    contentType:"application/json; charset=utf-8",
    dataType:"json",
    //data: updateField,
    success: function() {
      console.log("Module "+id+" completed running");
    //hide processing results view, replace with link to kibana
    document.getElementById("process-results").style.display = 'none';
    document.getElementById("results").style.display = 'block';
    //hide loader gif
    document.getElementById(image).style.display = 'none';
    //re-display page buttons
    for(var i=0; i< buttons.length; i++)
      buttons[i].style.display = 'block';
    document.getElementById("results-btn").style.display = 'inline-block';
    },
    error: function(){
      console.log("Unable to run module "+id);
      //hide processing results view, replace with error in results view
      document.getElementById("process-results").style.display = 'none';
      document.getElementById("error-results").style.display = 'block';
      //hide loader gif
      document.getElementById(image).style.display = 'none';
      //re-display page buttons
      for(var i=0; i< buttons.length; i++)
        buttons[i].style.display = 'block';
      //special button
      document.getElementById("results-btn").style.display = 'inline-block';
    }
  });
}

/**************************************************
*Import logs of specific type designated by id
*Disable all page buttons while importing
*Display loading gif for specific log import 
  during import
**************************************************/
function importerRun (id){
  var image = "importrun-img"+id;
  var buttons = document.getElementsByTagName('button');
  //display loader giv
  document.getElementById(image).style.display = 'block';
  //hide page buttons
  for(var i=0; i< buttons.length; i++)
    buttons[i].style.display = 'none';
  return $.ajax({
    type: "GET",
    url: BASE_URL + "importer/"+id+"/run", 
    contentType:"application/json; charset=utf-8",
    dataType:"json",
    success: function() {
    console.log("Import log "+id+" imported");
    //hide loader gif
    document.getElementById(image).style.display = 'none';
    //re-display page buttons
    for(var i=0; i< buttons.length; i++)
      buttons[i].style.display = 'block';
    document.getElementById("results-btn").style.display = 'inline-block';
    },
    error: function(){
      console.log("Unable to import log "+id);
      //hide loader gif
      document.getElementById(image).style.display = 'none';
      //re-display page buttons
      for(var i=0; i< buttons.length; i++)
        buttons[i].style.display = 'block';
      //special button
      document.getElementById("results-btn").style.display = 'inline-block';
    }
  });
}


/**************************************************
*Accept customer input from field indicated by id
*Pass new customer to page display and to customer
  input on settings tab
*Verify that tabs are now showing
*Verify that customer display on page is showing
*Verify that initial customer input is hidden
**************************************************/
function customerInput (id){
  var value = document.getElementById(id).value;
  var display  = document.getElementById("customerDisplay");
  var inputBox = document.getElementById("newCustomerInput");
  display.innerHTML = "";
  inputBox.value = "";
  display.innerHTML += value;
  inputBox.value += value;
  //hide initial customer input view
  document.getElementById("customer").style.display = 'none';
  //display customer name banner and tabs views
  document.getElementById("customerDisplay").style.display = 'block';
  document.getElementById("tabs").style.display = 'block';
  
  var updateField = "{\"customer\":\""+value+"\"}";
  return $.ajax({
    type: "POST",
    url: BASE_URL + "customer/set", 
    contentType:"application/json; charset=utf-8",
    dataType:"json",
    data: updateField,
    success: function()
    {console.log("Customer updated to "+value);},
    error: function()
    {console.log("Failed to update customer");}
  });
}


/**************************************************
Update server address on server
**************************************************/
function updateServer (){
  var server = document.getElementById('newServerInput').value;
  var updateField = "{\"server\":\""+server+"\"}";
  return $.ajax({
    type: "POST",
    url: BASE_URL + "esserver/set", 
    contentType:"application/json; charset=utf-8",
    dataType:"json",
    data: updateField,
    success: function()
    {console.log("Server updated to "+server);},
    error: function()
    {console.log("Failed to update server");}
  });
}

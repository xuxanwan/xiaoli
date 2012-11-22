// sid == selector(id)
var chartId;
var chartPath = 'olt-0';
var updateChart;

// Totally common
var config = {
  circle: {sid: '#chart', },
  flow: {sid: '#tchart', },
  interactive: {sid: '#tichart', }
}


function getTransform(selector){
  var transform = $(selector).attr("transform");
  if (!transform){
    transform = "translate(0,0)scale(1)";
  }
  var re = /^translate\((\S+),(\S+)\)scale\((\S+)\)/;
  var arr = re.exec(transform);
  return arr;
}


function transition(tar, start, end) {
  tar.attr("transform", transform(start))
    .transition()
    .delay(250)
    .duration(1000)
    .attrTween("transform", function() {return function(t) {return transform(t);}});
  
  function transform(t) {
    t = typeof(t) == "object" ? 0 : t;
    var x = t * (end[0]-start[0]) + start[0],
    y = t * (end[1]-start[1]) + start[1]
    k = t * (end[2]-start[2]) + start[2];
    return "transform", "translate("+ x +","+ y +")scale(" + k + ")";
  }
}

function countNodes(cur){
  var count = 0;
  if(cur && cur.children){
    count = cur.children.length;
    if(cur.children){
      for(var i=0; i< cur.children.length; i++) {
        count += countNodes(cur.children[i]);
      }
    }
  }
  return count;
}

function renderNodes(sid, node, collapse) {
  // 1. xlink, 2. image, 3. circle, 4. menu
  node.append("a")
    .attr("xlink:href", function(d){return d.url;});
  
  var a = node.selectAll('a')
    .append("svg:image")
    .attr("xlink:href", function(d){return "http://ww2.sinaimg.cn/large/412e82dbjw1dsbny7igx2j.jpg";})
    .attr("x", "-10px")
    .attr("y", "-10px")
    .attr("width", "20px")
    .attr("height", "20px");
  
  node.append("circle")
    .attr("r", 10)
    .attr("class", "status")
    .style("opacity", 0.3)
    .style("fill", function(d) { return d.status == 0 ? "red" : "green"});
  
  if (collapse){
    node.append("circle")
      .style("opacity", 1)
      .attr("r", 4.5)
      .attr("class", "collapse")
      .style("fill", function(d) { return d._children ? "#33D" : "#EEE"; });
  }
  
  addMenus(sid);
}

function addMenus(sid){
  $.contextMenu({
    selector: sid + ' .node', 
    callback: function(key, options) {
      var m = "clicked: " + $(this).find('text').text() + "\r\n\r\nAction: "
        + key + "\r\n\r\nTarget: " + $(this).find('a').attr('href');
      window.console && console.log(m) || alert(m); 
    },
    items: {
      "edit": {name: "Edit", icon: "edit"},
      "cut": {name: "Cut", icon: "cut"},
      "copy": {name: "Copy", icon: "copy"},
      "paste": {name: "Paste", icon: "paste"},
      "delete": {name: "Delete", icon: "delete"},
      "sep1": "---------",
      "quit": {name: "Quit", icon: "quit"}
    }
  });
}
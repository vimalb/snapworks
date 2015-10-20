document.APP_MODULES = document.APP_MODULES || [];

(function(){

var CONTROLLER_URL = document.currentScript.src;
var TEMPLATE_URL = CONTROLLER_URL.replace('controller.js','view.html');

var ROUTE_URL = '/landing';
var MODULE_NAME = 'mainApp'+URI(CONTROLLER_URL).path().replace('/src','').replace('/controller.js','').replace(/\//g,'.');
var CONTROLLER_NAME = MODULE_NAME.replace(/\./g,'_');
document.APP_MODULES.push(MODULE_NAME);

console.log(MODULE_NAME, "Registering route", ROUTE_URL);
angular.module(MODULE_NAME, ['ngRoute'])
  .config(function($routeProvider) {
    $routeProvider.when(ROUTE_URL, {
      templateUrl: TEMPLATE_URL,
      controller: CONTROLLER_NAME
    });
  })
  .controller(CONTROLLER_NAME, function($scope, CLIENT_SETTINGS, $http) {
    console.log("Loading controller", CONTROLLER_NAME);
    var SERVER_URL = CLIENT_SETTINGS.SERVER_URL;

    $scope.SERVER_URL = SERVER_URL;
    $scope.categories = [];
    $scope.selected_category = {}
    $scope.summary = {};
    $scope.chart1 = {};
    $scope.chart2 = {};
    $scope.chart3 = {};
    $scope.chart4 = {};

    $scope.setSelectedCategory = function(category) {
      $scope.selected_category = category;

      $http.get(SERVER_URL+'/api/dashboard/categories/'+category.name+'/issue_chart').then(function(resp){
        $scope.chart3 = resp.data;
      });

      $http.get(SERVER_URL+'/api/dashboard/categories/'+category.name+'/volunteer_chart').then(function(resp){
        $scope.chart4 = resp.data;
      });

    }

    $http.get(SERVER_URL+'/api/dashboard/categories').then(function(resp){
      $scope.categories = resp.data;
      $scope.setSelectedCategory($scope.categories[0]);
    });

    $http.get(SERVER_URL+'/api/dashboard/summary').then(function(resp){
      $scope.summary = resp.data;
    });

    $http.get(SERVER_URL+'/api/dashboard/issue_chart').then(function(resp){
      $scope.chart1 = resp.data;
    });

    $http.get(SERVER_URL+'/api/dashboard/volunteer_chart').then(function(resp){
      $scope.chart2 = resp.data;
    });

    
  });
  
  
})();
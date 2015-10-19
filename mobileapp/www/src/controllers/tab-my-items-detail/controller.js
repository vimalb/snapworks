document.APP_MODULES = document.APP_MODULES || [];

(function(){

var CONTROLLER_URL = document.currentScript.src;
var TEMPLATE_URL = CONTROLLER_URL.replace('controller.js','view.html');
var CONTROLLER_PATH = URI(CONTROLLER_URL).path();
CONTROLLER_PATH = CONTROLLER_PATH.substring(CONTROLLER_PATH.indexOf('/src/controllers/'));

var ROUTE_URL = '/my-items/:itemId';
var MODULE_NAME = 'mainApp'+CONTROLLER_PATH.replace('/src','').replace('/controller.js','').replace(/\//g,'.');
var CONTROLLER_NAME = MODULE_NAME.replace(/\./g,'_').replace(/-/g,'_');
document.APP_MODULES.push(MODULE_NAME);

console.log(MODULE_NAME, "Registering route", ROUTE_URL);
angular.module(MODULE_NAME, ['ionic'])
  .config(function($stateProvider) {
    $stateProvider.state('tab.my-items-detail', {
      url: ROUTE_URL,
      views: {
        'tab-my-items': {
          templateUrl: TEMPLATE_URL,
          controller: CONTROLLER_NAME
        }
      }
    });
  })
  .controller(CONTROLLER_NAME, function($scope, $stateParams, itemSearchService, userService, $state, CLIENT_SETTINGS) {
      $scope.SERVER_URL = CLIENT_SETTINGS.SERVER_URL;
      $scope.profiles = [];

      $scope.item = {};

      $scope.$on('$ionicView.beforeEnter', function(){
        generateProfilePics();
        itemSearchService.getItem($stateParams.itemId).then(function(item) {
          $scope.item = item;
        });
      });

      generateProfilePics = function() {
        $scope.profiles = [];
        var numberPics = Math.floor(Math.random()*3) + 2;
        var pics = [];
 
        var i = 0;
        while (i < numberPics) {
          var url = $scope.SERVER_URL;
          var j = Math.floor(Math.random() * 50);
          var coinFlip = Math.random();

          if (coinFlip > 0.5) {
            url = url +'/profiles/woman'+j+'.jpg';
            $scope.profiles.push(url);
          } else {
            url = url +'/profiles/woman'+j+'.jpg';
            $scope.profiles.push(url);
          }
          i += 1;
        }
      }

      $scope.$on('$ionicView.beforeLeave', function(){
        $scope.item = {};
      });
  })


})();


document.APP_MODULES = document.APP_MODULES || [];

(function(){

var CONTROLLER_URL = document.currentScript.src;
var TEMPLATE_URL = CONTROLLER_URL.replace('controller.js','view.html');
var CONTROLLER_PATH = URI(CONTROLLER_URL).path();
CONTROLLER_PATH = CONTROLLER_PATH.substring(CONTROLLER_PATH.indexOf('/src/controllers/'));

var ROUTE_URL = '/my-actions';
var MODULE_NAME = 'mainApp'+CONTROLLER_PATH.replace('/src','').replace('/controller.js','').replace(/\//g,'.');
var CONTROLLER_NAME = MODULE_NAME.replace(/\./g,'_').replace(/-/g,'_');
document.APP_MODULES.push(MODULE_NAME);

console.log(MODULE_NAME, "Registering route", ROUTE_URL);
angular.module(MODULE_NAME, ['ionic'])
  .config(function($stateProvider) {
    $stateProvider.state('tab.my-actions', {
        url: ROUTE_URL,
        views: {
          'tab-my-actions': {
            templateUrl: TEMPLATE_URL,
            controller: CONTROLLER_NAME
          }
        }
      });
  })
  .controller(CONTROLLER_NAME, function($scope, itemSearchService, $state, CLIENT_SETTINGS) {
    console.log("Instantiating controller", CONTROLLER_NAME);

    $scope.items = [];
    $scope.SERVER_URL = CLIENT_SETTINGS.SERVER_URL;

    $scope.init = function() {
      if($localStorage.hasOwnProperty("accessToken") === true) {
        $http.get("https://graph.facebook.com/v2.2/me", { params: { access_token: $localStorage.accessToken, fields: "id,name,gender,location,website,picture,relationship_status", format: "json" }}).then(function(result) {
            $scope.profileData = result.data;
        }, function(error) {
            alert("There was a problem getting your profile.  Check the logs for details.");
            console.log(error);
        });
      } else {
        console.log("Not signed in");
      }
    }

    $scope.refreshItems = function() {
      itemSearchService.getNearbyItems().then(function(items) {
        $scope.items = items;
      });
    }

    $scope.$on('$ionicView.beforeEnter', function(){
      $scope.refreshItems();
    });

    $scope.goItemDetail = function(itemId) {
      $state.go('tab.my-actions-detail', {itemId: itemId});
    }

    /*$scope.showItemComments = function(item) {
      if(item.showComments == true) {
        item.showComments = false;
      }
      else
      {
        item.showComments = true;
      }
      return item.showComments;
    }*/
  })
})();


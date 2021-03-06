document.APP_MODULES = document.APP_MODULES || [];

(function(){

var CONTROLLER_URL = document.currentScript.src; var TEMPLATE_URL = CONTROLLER_URL.replace('controller.js','view.html');
var CONTROLLER_PATH = URI(CONTROLLER_URL).path();
CONTROLLER_PATH = CONTROLLER_PATH.substring(CONTROLLER_PATH.indexOf('/src/controllers/'));

var ROUTE_URL = '/login';
var MODULE_NAME = 'mainApp'+CONTROLLER_PATH.replace('/src','').replace('/controller.js','').replace(/\//g,'.');
//var CONTROLLER_NAME = MODULE_NAME.replace(/\./g,'_').replace(/-/g,'_');
var CONTROLLER_NAME = 'LoginController';
document.APP_MODULES.push(MODULE_NAME);


angular.module(MODULE_NAME, ['ionic', 'ngStorage', 'ngCordova'])
  .config(function($stateProvider) {
    $stateProvider.state('tab.login', {
      url: ROUTE_URL,
      views: {
        'tab-my-pledges': {
          templateUrl: TEMPLATE_URL,
          controller: CONTROLLER_NAME
        }
      }
    });
  })
  .controller(CONTROLLER_NAME, function($scope, $state, $cordovaOauth, $http, $stateParams, $localStorage, $location, userService) {
    console.log("Instantiating controller", CONTROLLER_NAME);
    window.cordovaOauth = $cordovaOauth;
    window.http = $http;
    $scope.loggedIn = false;


    var displayData = function(access_token)
    {
        $http.get("https://graph.facebook.com/v2.2/me", {params: {access_token: access_token, fields: "name,gender,location,picture", format: "json" }}).then(function(result) {
            var name = result.data.name;
            var gender = result.data.gender;
            var picture = result.data.picture;

            currentUser = userService.getCurrentUser();
            currentUser.name = name.split(' ')[0];
            currentUser.photo_url = picture.data.url;


            var htmlHeader = "<div class='card avatar'><div class='item item-avatar header'><img class='profile-img' src='"+picture.data.url+"'> <h2>"+name+"</h2></div></div>";

            //document.getElementById("profileHeader").innerHTML = htmlHeader;
            //document.getElementById("login-button").className = "hide";

            //document.getElementsByClassName("sign-in-text")[0].className = "sign-in-text hide";
            //document.getElementsByClassName("success")[0].className -= "hide";
            
        }, function(error) {
            alert("Error: " + error);
        });
    }


    $scope.facebookLogin = function() {
      console.log('Logging in with Facebook');
      $cordovaOauth.facebook("1466619133643813", ["email", "public_profile"], {redirect_uri: "http://localhost/callback"}).then(function(result) {
        $localStorage.accessToken = result.access_token;
        userService.getCurrentUser().access_token = result.access_token;
        displayData(result.access_token);
        $scope.loggedIn = true;
        $state.go("tab.my-trips");
        //$state.go($stateParams.from); <-- this crashes the app`
      }, function(error) {
          // error
          console.dir(error);
      });
    }

    $scope.$on('$ionicView.beforeEnter', function(){
    });

    $scope.goToFeed = function () {
      $state.go('tab.my-trips');
    }
  })

})();

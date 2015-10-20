document.APP_MODULES = document.APP_MODULES || [];

(function(){

var CONTROLLER_URL = document.currentScript.src;
var TEMPLATE_URL = CONTROLLER_URL.replace('controller.js','view.html');
var CONTROLLER_PATH = URI(CONTROLLER_URL).path();
CONTROLLER_PATH = CONTROLLER_PATH.substring(CONTROLLER_PATH.indexOf('/src/controllers/'));

var ROUTE_URL = '/my-feed';
var MODULE_NAME = 'mainApp'+CONTROLLER_PATH.replace('/src','').replace('/controller.js','').replace(/\//g,'.');
var CONTROLLER_NAME = MODULE_NAME.replace(/\./g,'_').replace(/-/g,'_');
document.APP_MODULES.push(MODULE_NAME);

console.log(MODULE_NAME, "Registering route", ROUTE_URL);
angular.module(MODULE_NAME, ['ionic', 'ngStorage'])
  .config(function($stateProvider) {
    $stateProvider.state('tab.my-feed', {
        url: ROUTE_URL,
        views: {
          'tab-my-feed': {
            templateUrl: TEMPLATE_URL,
            controller: CONTROLLER_NAME
          }
        }
      });
  })
  .controller(CONTROLLER_NAME, function($scope, itemSearchService, $state, $timeout, $localStorage, userService, CLIENT_SETTINGS) {
    console.log("Instantiating controller", CONTROLLER_NAME);

    $scope.cameraInfo = { isEnabled: false };
    $scope.photoInfo = null;
    $scope.reportedIssue = null;
    $scope.state = 'taking_photo'; // taking_photo, choosing_issue, uploading_issue, confirming_issue
    $scope.SERVER_URL = CLIENT_SETTINGS.SERVER_URL;

    $scope.resetPhoto = function() {
      $scope.cameraInfo.isEnabled = true;
      $scope.photoInfo = null;      
      $scope.reportedIssue = null;
      $scope.state = 'taking_photo';
    }

    $scope.takeSnapshot = function() {
      $scope.cameraInfo.takePicture();
    }

    $scope.switchCam = function() {
      $scope.cameraInfo.switchCamera();
    }

    $scope.onSnapshotTaken = function(base64photo) {
      $scope.cameraInfo.isEnabled = false;
      $scope.photoInfo = base64photo;
      $scope.state = 'choosing_issue';
    }


    $scope.reportIssue = function() {
      var issueType = $("input[name=report_type]:checked").val();
      var issue = {'issue_type': issueType,
                   'photo': $scope.photoInfo }
      $scope.state = 'uploading_issue';
      itemSearchService.createItem(issue).then(function(newIssue) {
        $scope.state = 'confirming_issue';
        $scope.reportedIssue = newIssue;
        $timeout(function() {
          $scope.resetPhoto();
        }, 2000);
      });
    }


    $scope.$on('$ionicView.beforeEnter', function(){
      $scope.resetPhoto();
    });

    $scope.$on('$ionicView.beforeLeave', function(){
      $scope.cameraInfo.isEnabled = false;
    });

  })

})();


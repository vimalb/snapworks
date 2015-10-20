document.APP_MODULES = document.APP_MODULES || [];

(function(){

var CONTROLLER_URL = document.currentScript.src;
var TEMPLATE_URL = CONTROLLER_URL.replace('controller.js','view.html');
var CONTROLLER_PATH = URI(CONTROLLER_URL).path();
CONTROLLER_PATH = CONTROLLER_PATH.substring(CONTROLLER_PATH.indexOf('/src/controllers/'));

var ROUTE_URL = '/my-actions/:itemId';
var MODULE_NAME = 'mainApp'+CONTROLLER_PATH.replace('/src','').replace('/controller.js','').replace(/\//g,'.');
var CONTROLLER_NAME = MODULE_NAME.replace(/\./g,'_').replace(/-/g,'_');
document.APP_MODULES.push(MODULE_NAME);

console.log(MODULE_NAME, "Registering route", ROUTE_URL);
angular.module(MODULE_NAME, ['ionic', 'ngCordova'])
  .config(function($stateProvider) {
    $stateProvider.state('tab.my-actions-detail', {
      url: ROUTE_URL,
      views: {
        'tab-my-actions': {
          templateUrl: TEMPLATE_URL,
          controller: CONTROLLER_NAME
        }
      }
    });
  })
  .controller(CONTROLLER_NAME, function($scope, $stateParams, itemSearchService, userService, $state, $cordovaSocialSharing, CLIENT_SETTINGS, $timeout, $interval) {
      $scope.item = {};
      $scope.SERVER_URL = CLIENT_SETTINGS.SERVER_URL;

      $scope.messages = [];
      $scope.newMessage = {'text': ''};
      $scope.self_like = false;
      $scope.self_volunteer = false;
      $scope.like_count = 0;
      $scope.volunteer_count = 0;
      $scope.message_count = 0;

      $scope.loadMessages = function() {
        itemSearchService.getMessages($scope.item.item_id).then(function(messages) {
          $scope.updateMessages(messages);
          //console.log(messages);
        });
      }

      $scope.updateMessages = function(messages) {
          $scope.messages = messages;

          $scope.self_like = false;
          $scope.self_volunteer = false;
          $scope.like_count = 0;
          $scope.volunteer_count = 0;
          $scope.message_count = 0;

          _.each(messages, function(message) {
            $scope.message_count = $scope.message_count + 1;
            if(message.volunteer) {
              $scope.volunteer_count = $scope.volunteer_count + 1;
              if(message.user.user_id == userService.getCurrentUser().user_id) {
                $scope.self_volunteer = true;
              }
            }
            if(message.like) {
              $scope.like_count = $scope.like_count + 1;
              if(message.user.user_id == userService.getCurrentUser().user_id) {
                $scope.self_like = true;
              }
            }
          });
      }

      $scope.likeItem = function() {
        if(!$scope.self_like) {
          itemSearchService.sendMessage($scope.item.item_id, {'like': true, 'text':'Liked this'}).then(function(messages) {
            $scope.updateMessages(messages);
          });
        }
      }

      $scope.volunteerItem = function() {
        if(!$scope.self_volunteer) {
          itemSearchService.sendMessage($scope.item.item_id, {'volunteer': true, 'text':'Volunteered to help fix this!'}).then(function(messages) {
            $scope.updateMessages(messages);
          });
        }
      }


      $scope.submitMessage = function() {
        if($scope.newMessage.text) {
          itemSearchService.sendMessage($scope.item.item_id, $scope.newMessage).then(function(messages) {
            $scope.newMessage.text = '';
            $scope.messages = messages;
          });
        }
      }

      $scope.$on('$ionicView.beforeEnter', function(){
        console.log('stateParams', $stateParams);
        itemSearchService.getItem($stateParams.itemId).then(function(item) {
          $scope.item = item;
          console.log(item);
          $scope.loadMessages();
          $scope.pollInterval = $interval(function() {
            $scope.loadMessages();
          }, 2000);
        });
      });

      $scope.$on('$ionicView.beforeLeave', function(){
        $scope.item = {};
        if($scope.pollInterval) {
          $interval.cancel($scope.pollInterval);
          $scope.pollInterval = undefined;
        }
      });


      $scope.shareOnFacebook = function () {
        var message = null;
        var image = null;
        var link = $scope.SERVER_URL+'/share/'+$scope.item.item_id;
        
        $cordovaSocialSharing
          .shareViaFacebook(message, image, link)
          .then(function(result) {
            console.log(link, 'shared via facebook!');
          }, function(err) {
            // An error occurred. Show a message to the user
             console.log(link, 'Facebook share failed');
             console.dir(err.toString());
          });
      }

  })


})();


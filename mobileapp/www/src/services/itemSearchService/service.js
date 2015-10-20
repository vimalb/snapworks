document.APP_MODULES = document.APP_MODULES || [];

(function(){

var SERVICE_URL = document.currentScript.src;
var SERVICE_PATH = URI(SERVICE_URL).path();
SERVICE_PATH = SERVICE_PATH.substring(SERVICE_PATH.indexOf('/src/services/'));

var MODULE_NAME = 'mainApp'+SERVICE_PATH.replace('/src','').replace('/service.js','').replace(/\//g,'.');
var SERVICE_NAME = SERVICE_PATH.replace('/src/services/','').replace('/service.js','').replace(/\//g,'');

document.APP_MODULES.push(MODULE_NAME);

console.log(MODULE_NAME, "Registering service", SERVICE_NAME);
angular.module(MODULE_NAME, [])
    .factory(SERVICE_NAME, function($q, CLIENT_SETTINGS, $http, userService) {
      console.log("Instantiating service", SERVICE_NAME);

      return {
        getMyFeed: function() {
          console.log("Fetching my feed");
          var deferred = $q.defer();
          var url = CLIENT_SETTINGS.SERVER_URL + '/api/users/' + userService.getCurrentUser().user_id + '/feed';
          $http.get(url).then(function(resp) {
            deferred.resolve(resp.data);
          });
          return deferred.promise;
        },

        getMyItems: function() {
          console.log("Fetching my routes");
          var deferred = $q.defer();
          var url = CLIENT_SETTINGS.SERVER_URL + '/api/users/' + userService.getCurrentUser().user_id + '/items';
          $http.get(url).then(function(resp) {
            deferred.resolve(resp.data);
          });
          return deferred.promise;
        },

        getPopularItems: function() {
          console.log("Fetching popular routes");
          var deferred = $q.defer();
          var url = CLIENT_SETTINGS.SERVER_URL + '/api/items/popular';
          $http.get(url).then(function(resp) {
            deferred.resolve(resp.data);
          });
          return deferred.promise;
        },

        getNearbyItems: function() {
          console.log("Fetching popular routes");
          var deferred = $q.defer();
          var url = CLIENT_SETTINGS.SERVER_URL + '/api/items/nearby';
          navigator.geolocation.getCurrentPosition(function (pos) {
            var location = {'latitude': pos.coords.latitude,
                             'longitude': pos.coords.longitude,
                             'timestamp': (new Date()).toISOString()};
            $http.post(url, JSON.stringify(location)).then(function(resp) {
              deferred.resolve(resp.data);
            });
          });
          return deferred.promise;
        },


        createItem: function(item) {
          var deferred = $q.defer();
          var url = CLIENT_SETTINGS.SERVER_URL + '/api/users/' + userService.getCurrentUser().user_id + '/items';
          navigator.geolocation.getCurrentPosition(function (pos) {
            item.location = {'latitude': pos.coords.latitude,
                             'longitude': pos.coords.longitude };
            item.timestamp = (new Date()).toISOString();
            $http.post(url, JSON.stringify(item)).then(function(resp) {
              deferred.resolve(resp.data);
            });
          });
          return deferred.promise;
        },


        getItem: function(itemId) {
          console.log("Fetching item", itemId);
          var deferred = $q.defer();
          var url = CLIENT_SETTINGS.SERVER_URL + '/api/items/all/' + itemId.toString();
          $http.get(url).then(function(resp) {
            deferred.resolve(resp.data);
          });
          return deferred.promise;
        },

        getMessages: function(itemId) {
          console.log("Fetching messages for item", itemId);
          var deferred = $q.defer();
          var url = CLIENT_SETTINGS.SERVER_URL + '/api/items/all/' + itemId.toString() + '/messages';
          $http.get(url).then(function(resp) {
            deferred.resolve(resp.data);
          });
          return deferred.promise;
        },

        sendMessage: function(itemId, message) {
          console.log("Sending message for item", itemId, message);
          var deferred = $q.defer();
          var url = CLIENT_SETTINGS.SERVER_URL + '/api/items/all/' + itemId.toString() + '/messages';
          message.user = userService.getCurrentUser();
          message.timestamp = (new Date()).toISOString();
          $http.post(url, JSON.stringify(message)).then(function(resp) {
            deferred.resolve(resp.data);
          });
          return deferred.promise;
        },


      };

    });


})();

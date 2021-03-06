document.APP_MODULES = document.APP_MODULES || [];

(function() {

ALL_MODULES = [ 'ionic', 
                'ngTagsInput',
                'uiGmapgoogle-maps',
                'omr.directives',
                ].concat(document.APP_MODULES);

angular.module('mainApp', ALL_MODULES)
    .config(function($urlRouterProvider, $ionicConfigProvider) {
      $ionicConfigProvider.tabs.style('standard');
      $ionicConfigProvider.tabs.position('bottom');
      $urlRouterProvider.otherwise('/tab/my-feed');
    })
    .config(function(uiGmapGoogleMapApiProvider) {
        uiGmapGoogleMapApiProvider.configure({
            //    key: 'your api key',
            v: '3.20', //defaults to latest 3.X anyhow
            libraries: 'weather,geometry,visualization'
        });
    })
    .run(function($ionicPlatform) {
      $ionicPlatform.ready(function() {
        // Hide the accessory bar by default (remove this to show the accessory bar above the keyboard
        // for form inputs)
        if (window.cordova && window.cordova.plugins && window.cordova.plugins.Keyboard) {
          cordova.plugins.Keyboard.hideKeyboardAccessoryBar(true);
          cordova.plugins.Keyboard.disableScroll(true);

        }
        if (window.StatusBar) {
          // org.apache.cordova.statusbar required
          StatusBar.styleLightContent();
        }
      });
    });

    
deferredBootstrapper.bootstrap({
  element: document.body,
  module: 'mainApp',
  resolve: {
    CLIENT_SETTINGS: ['$q', function ($q) {
      var deferred = $q.defer();
      deferred.resolve(document.CLIENT_SETTINGS);
      return deferred.promise;
    }],
    SERVER_SETTINGS: ['$http', function ($http) {
      return $http.get(document.CLIENT_SETTINGS.SERVER_URL+'/settings/server');
    }],
    SOCKET_IO_CLIENT: ['$q', function ($q) {
      var deferred = $q.defer();
      $.getScript(document.CLIENT_SETTINGS.SERVER_URL+'/socket.io/socket.io.js', function() {
          deferred.resolve();
      });
      return deferred.promise;
    }],
    VIDEO_SOURCES: ['$q', function ($q) {
      var deferred = $q.defer();

      MediaStreamTrack.getSources(function(sources) {
        var availableSources = [];
        _.each(sources, function(source) {
          if(source.kind == 'video') {
            availableSources.push(source.id);
          }
        });
        deferred.resolve(availableSources);
      });
      return deferred.promise;
    }],
  }
});
    

})()
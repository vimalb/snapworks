document.APP_MODULES = document.APP_MODULES || [];

(function(){

var DIRECTIVE_URL = document.currentScript.src;
var TEMPLATE_URL = DIRECTIVE_URL.replace('directive.js','view.html');
var DIRECTIVE_PATH = URI(DIRECTIVE_URL).path();
DIRECTIVE_PATH = DIRECTIVE_PATH.substring(DIRECTIVE_PATH.indexOf('/src/directives/'));

var MODULE_NAME = 'mainApp'+DIRECTIVE_PATH.replace('/src','').replace('/directive.js','').replace(/\//g,'.');
var DIRECTIVE_NAME = DIRECTIVE_PATH.replace('/src/directives/','').replace('/directive.js','').replace(/\//g,'');

document.APP_MODULES.push(MODULE_NAME);



console.log(MODULE_NAME, "Registering directive", DIRECTIVE_NAME);
angular.module(MODULE_NAME, [])
  .directive(DIRECTIVE_NAME, function($http, CLIENT_SETTINGS, SERVER_SETTINGS, uiGmapGoogleMapApi, $timeout) {
    console.log("Loading directive", DIRECTIVE_NAME);

    return {
        restrict: 'E', //E = element, A = attribute, C = class, M = comment         
        scope: {
            trip: '=',
            },
        templateUrl: TEMPLATE_URL,
        link: function ($scope, element, attrs) { 

            $scope.map = {};

            var coordToStr = function(coord) {
              if( Object.prototype.toString.call( coord ) === '[object Array]' ) {
                return coord[0].toString()+','+coord[1].toString();
              }
              else {
                return coord.latitude.toString()+','+coord.longitude.toString();
              }
            } 

            var canMergeLegs = function(leg1, leg2) {
              return leg1.stroke.color == leg2.stroke.color;
            }

            var renderTrip = function() {
              var startPos = $scope.trip.legs[0].start;
              var finishPos = $scope.trip.legs[$scope.trip.legs.length - 1].end;
              uiGmapGoogleMapApi.then(function(maps) {
                $scope.map = { bounds: {},
                               center: { latitude: (startPos[0] + finishPos[0]) / 2.0, longitude: (startPos[1] + finishPos[1]) / 2.0 },
                               zoom: 14
                             };
                $timeout(function() {
                  $scope.map.bounds = { northeast: { latitude: Math.max(startPos[0], finishPos[0]), longitude: Math.max(startPos[1], finishPos[1]) }, 
                                        southwest: { latitude: Math.min(startPos[0], finishPos[0]), longitude: Math.min(startPos[1], finishPos[1]) } };
                  $scope.map.polylines = [];
                  _.each($scope.trip.legs, function(leg) { 

                    var leg_color = '#6060FB';
                    if(leg.warning_level == 'Clear' && leg.nominal_kmph > 75.0) {
                      leg_color = '#10FF00'
                    }
                    else if(leg.warning_level == 'Clear' && leg.nominal_kmph <= 75.0 && leg.nominal_kmph > 65.0) {
                      leg_color = '#40FF00'
                    }
                    else if(leg.warning_level == 'Clear' && leg.nominal_kmph <= 65.0 && leg.nominal_kmph > 55.0) {
                      leg_color = '#80FF00'
                    }
                    else if(leg.warning_level == 'Clear' && leg.nominal_kmph <= 55.0 && leg.nominal_kmph > 45.0) {
                      leg_color = '#C0FF00'
                    }
                    else if(leg.warning_level == 'Clear' && leg.nominal_kmph <= 45.0 && leg.nominal_kmph > 35.0) {
                      leg_color = '#FFFF00'
                    }
                    else if(leg.warning_level == 'Clear' && leg.nominal_kmph <= 35.0 && leg.nominal_kmph > 25.0) {
                      leg_color = '#FFC000'
                    }
                    else if(leg.warning_level == 'Clear' && leg.nominal_kmph <= 25.0) {
                      leg_color = '#FF8000'
                    }
                    else if(leg.warning_level == 'Low Impact') {
                      leg_color = '#FFFF00'
                    }
                    else if(leg.warning_level == 'Minor') {
                      leg_color = '#FFFF00'
                    }
                    else if(leg.warning_level == 'Moderate') {
                      leg_color = '#10FF00'
                    }
                    else if(leg.warning_level == 'Serious') {
                      leg_color = '#10FF00'
                    }
                    proposed_path = {path: [ { latitude: leg.start[0], longitude: leg.start[1] },
                                         { latitude: leg.end[0], longitude: leg.end[1] },
                                       ],
                            stroke: {
                                  color: leg_color,
                                  weight: 3
                              },
                            visible: true,
                            editable: false,
                            draggable: false,
                            geodesic: true,
                            /*
                            icons: [{
                                      icon: {
                                          path: google.maps.SymbolPath.BACKWARD_OPEN_ARROW
                                      },
                                      offset: '25px',
                                      repeat: '50px'
                                  }],
                            */
                            };
                    if($scope.map.polylines.length > 0 && canMergeLegs($scope.map.polylines[$scope.map.polylines.length-1], proposed_path)) {
                      $scope.map.polylines[$scope.map.polylines.length-1].path.push({ latitude: leg.end[0], longitude: leg.end[1] });
                    }
                    else {
                      $scope.map.polylines.push(proposed_path);  
                    }
                  });

                  $scope.map.markers = [{ coords: { latitude: startPos[0], longitude: startPos[1] },
                                          options: { },
                                          icon: 'http://maps.google.com/mapfiles/ms/icons/red-dot.png' ,
                                          id: 0,
                                        },
                                        { coords: { latitude: finishPos[0], longitude: finishPos[1] },
                                          options: { },
                                          icon: 'http://maps.google.com/mapfiles/ms/icons/green-dot.png' ,
                                          id: 1,
                                        },
                                        ];


                  var staticUri = URI('https://maps.googleapis.com/maps/api/staticmap');
                  var mapUriParams = {  'size': '330x350',
                                        'markers': [ 'color:red|'+coordToStr(startPos), 'color:green|'+coordToStr(finishPos)],
                                        'path': _.map(_.sample($scope.trip.legs, 20), function(leg) {
                                          return 'color:blue|'+coordToStr(leg.start)+'|'+coordToStr(leg.end);
                                        }),

                                      }
                  staticUri.addQuery(mapUriParams);
                  $scope.map.url = staticUri.toString();

                  console.log('trip', $scope.trip);
                  console.log('map', $scope.map);
                  
                }, 10);
              });
            }

            $scope.$watch('trip', function() {
              renderTrip();
            });

            renderTrip();

        }
    }
    
  });
  
  
})();
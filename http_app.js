/**
 * Copyright (c) 2018, OCEAN
 * All rights reserved.
 * Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:
 * 1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
 * 2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
 * 3. The name of the author may not be used to endorse or promote products derived from this software without specific prior written permission.
 * THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 */

/**
 * Created by ryeubi on 2015-08-31.
 */

var http = require('http');
var express = require('express');
var fs = require('fs');
var mqtt = require('mqtt');
var util = require('util');
var url = require('url');
var ip = require('ip');
var shortid = require('shortid');
var moment = require('moment');

var spawn = require('child_process').spawn;

global.sh_adn = require('./http_adn');
var noti = require('./noti');

var HTTP_SUBSCRIPTION_ENABLE = 0;
var MQTT_SUBSCRIPTION_ENABLE = 0;

global.my_data_name = '';
global.dry_roadcell = '';
global.my_parent_cnt_name = '';
global.my_cnt_name = '';
global.pre_my_cnt_name = '';
global.my_mission_parent = '';
global.my_mission_name = '';
global.zero_parent_mission_name = '';
global.zero_mission_name = '';
global.my_sortie_name = 'disarm';
// global.my_drone_type = 'pixhawk';
global.my_secure = 'off';

const first_interval = 3000;
const retry_interval = 2500;
const normal_interval = 100;
const data_interval = 2000;
const display_interval = 1000;

const always_interval = 30000;
const always_period_tick = parseInt((3 * 60 * 1000) / always_interval);

const debug_pin = 12;
const operation_pin = 18;
const start_btn_pin = 13;
const solenoid_pin = 14;
const fan_pin = 15;
const input_door_pin = 16;
const output_door_pin = 17;
const safe_door_pin = 18;
const heater1_pin = 19;
const heater2_pin = 20;
const heater3_pin = 21;
const stirrer_pin = 22;

var app = express();

//app.use(bodyParser.urlencoded({ extended: true }));
//app.use(bodyParser.json());
//app.use(bodyParser.json({ type: 'application/*+json' }));
//app.use(bodyParser.text({ type: 'application/*+xml' }));

var dryer_event = 0x00;

const EVENT_INPUT_DOOR_OPEN = 0x01;
const EVENT_INPUT_DOOR_CLOSE = 0x02;
const EVENT_OUTPUT_DOOR_OPEN = 0x04;
const EVENT_OUTPUT_DOOR_CLOSE = 0x08;
const EVENT_SAFE_DOOR_OPEN = 0x10;
const EVENT_SAFE_DOOR_CLOSE = 0x20;
const EVENT_START_BTN_CLICK = 0x40;
const EVENT_START_BTN_LONG = 0x80;

/*
var tas_dryer = spawn('python3', ['./exec.py']);
tas_dryer.stdout.on('data', function(data) {
    console.log('stdout: ' + data);
});
tas_dryer.on('exit', function(code) {
    console.log('exit: ' + code);
});
tas_dryer.on('error', function(code) {
    console.log('error: ' + code);
});*/

// ?????? ????????.
var server = null;
var noti_topic = '';

// ready for mqtt
for(var i = 0; i < conf.sub.length; i++) {
    if(conf.sub[i].name != null) {
        if(url.parse(conf.sub[i].nu).protocol === 'http:') {
            HTTP_SUBSCRIPTION_ENABLE = 1;
            if(url.parse(conf.sub[i]['nu']).hostname === 'autoset') {
                conf.sub[i]['nu'] = 'http://' + ip.address() + ':' + conf.ae.port + url.parse(conf.sub[i]['nu']).pathname;
            }
        }
        else if(url.parse(conf.sub[i].nu).protocol === 'mqtt:') {
            MQTT_SUBSCRIPTION_ENABLE = 1;
        }
        else {
            //console.log('notification uri of subscription is not supported');
            //process.exit();
        }
    }
}

var return_count = 0;
var request_count = 0;

function ready_for_notification() {
    if(HTTP_SUBSCRIPTION_ENABLE == 1) {
        server = http.createServer(app);
        server.listen(conf.ae.port, function () {
            console.log('http_server running at ' + conf.ae.port + ' port');
        });
    }

    if(MQTT_SUBSCRIPTION_ENABLE == 1) {
        for(var i = 0; i < conf.sub.length; i++) {
            if (conf.sub[i].name != null) {
                if (url.parse(conf.sub[i].nu).protocol === 'mqtt:') {
                    if (url.parse(conf.sub[i]['nu']).hostname === 'autoset') {
                        conf.sub[i]['nu'] = 'mqtt://' + conf.cse.host + '/' + conf.ae.id;
                        noti_topic = util.format('/oneM2M/req/+/%s/#', conf.ae.id);
                    }
                    else if (url.parse(conf.sub[i]['nu']).hostname === conf.cse.host) {
                        noti_topic = util.format('/oneM2M/req/+/%s/#', conf.ae.id);
                    }
                    else {
                        noti_topic = util.format('%s', url.parse(conf.sub[i].nu).pathname);
                    }
                }
            }
        }
        //mqtt_connect(conf.cse.host, noti_topic);
    }
}

function ae_response_action(status, res_body, callback) {
    var aeid = res_body['m2m:ae']['aei'];
    conf.ae.id = aeid;
    callback(status, aeid);
}

function create_cnt_all(count, callback) {
    if(conf.cnt.length == 0) {
        callback(2001, count);
    }
    else {
        if(conf.cnt.hasOwnProperty(count)) {
            var parent = conf.cnt[count].parent;
            var rn = conf.cnt[count].name;
            sh_adn.crtct(parent, rn, count, function (rsc, res_body, count) {
                if (rsc == 5106 || rsc == 2001 || rsc == 4105) {
                    create_cnt_all(++count, function (status, count) {
                        callback(status, count);
                    });
                }
                else {
                    callback(9999, count);
                }
            });
        }
        else {
            callback(2001, count);
        }
    }
}

function delete_sub_all(count, callback) {
    if(conf.sub.length == 0) {
        callback(2001, count);
    }
    else {
        if(conf.sub.hasOwnProperty(count)) {
            var target = conf.sub[count].parent + '/' + conf.sub[count].name;
            sh_adn.delsub(target, count, function (rsc, res_body, count) {
                if (rsc == 5106 || rsc == 2002 || rsc == 2000 || rsc == 4105 || rsc == 4004) {
                    delete_sub_all(++count, function (status, count) {
                        callback(status, count);
                    });
                }
                else {
                    callback(9999, count);
                }
            });
        }
        else {
            callback(2001, count);
        }
    }
}

function create_sub_all(count, callback) {
    if(conf.sub.length == 0) {
        callback(2001, count);
    }
    else {
        if(conf.sub.hasOwnProperty(count)) {
            var parent = conf.sub[count].parent;
            var rn = conf.sub[count].name;
            var nu = conf.sub[count].nu;
            sh_adn.crtsub(parent, rn, nu, count, function (rsc, res_body, count) {
                if (rsc == 5106 || rsc == 2001 || rsc == 4105) {
                    create_sub_all(++count, function (status, count) {
                        callback(status, count);
                    });
                }
                else {
                    callback('9999', count);
                }
            });
        }
        else {
            callback(2001, count);
        }
    }
}

var dry_info = {};

function retrieve_my_cnt_name(callback) {
    sh_adn.rtvct('/Mobius/DRY/approval/'+conf.ae.name+'/la', 0, function (rsc, res_body, count) {
        if(rsc == 2000) {
            dry_info = res_body[Object.keys(res_body)[0]].con;
            // // console.log(drone_info);

            conf.cnt = [];
            var info = {};
            info.parent = '/Mobius/' + dry_info.space;// /Mobius/KETI_DRY
            info.name = 'Dry_Data';
            conf.cnt.push(JSON.parse(JSON.stringify(info)));

            info.parent = '/Mobius/' + dry_info.space + '/Dry_Data';// /Mobius/KETI_DRY/Dry_Data
            info.name = dry_info.dry;
            conf.cnt.push(JSON.parse(JSON.stringify(info)));

            info.parent = '/Mobius/' + dry_info.space + '/Dry_Data/' + dry_info.dry; // /Mobius/KETI_DRY/Dry_Data/keti
            info.name = my_sortie_name; // /Mobius/KETI_DRY/Dry_Data/keti/disarm
            conf.cnt.push(JSON.parse(JSON.stringify(info)));

            my_parent_cnt_name = info.parent; // /Mobius/KETI_DRY/Dry_Data/keti/
            my_cnt_name = my_parent_cnt_name + '/' + my_sortie_name; // /Mobius/KETI_DRY/Dry_Data/keti/

            info.parent = '/Mobius/' + dry_info.space;// /Mobius/KETI_DRY
            info.name = 'Zero_Data';
            conf.cnt.push(JSON.parse(JSON.stringify(info)));

            info.parent = '/Mobius/' + dry_info.space + '/Zero_Data';
            info.name = dry_info.dry;
            conf.cnt.push(JSON.parse(JSON.stringify(info)));

            // default mission
            info.parent = '/Mobius/' + dry_info.space + '/Zero_Data/' + dry_info.dry;
            info.name = 'Adjustment';
            conf.cnt.push(JSON.parse(JSON.stringify(info)));

            zero_parent_mission_name = info.parent + '/' + info.name;
            zero_mission_name = zero_parent_mission_name + '/' + my_sortie_name;

            info.parent = zero_parent_mission_name;
            info.name = my_sortie_name;
            conf.cnt.push(JSON.parse(JSON.stringify(info)));

            if(dry_info.hasOwnProperty('loadcell_factor')) {
                dry_data_block.loadcell_factor = dry_info.loadcell_factor;
            }

            if(dry_info.hasOwnProperty('cum_ref_weight')) {
                dry_data_block.cum_ref_weight = dry_info.cum_ref_weight;
            }

            if(dry_info.hasOwnProperty('loadcell_ref_weight')) {
                dry_data_block.loadcell_ref_weight = dry_info.loadcell_ref_weight;
            }

            MQTT_SUBSCRIPTION_ENABLE = 1;
            sh_state = 'crtct';
            setTimeout(http_watchdog, normal_interval);
            callback();
        }
        else {
            console.log('x-m2m-rsc : ' + rsc + ' <----' + res_body);
            setTimeout(http_watchdog, retry_interval);
            callback();
        }
    });
}

setTimeout(http_watchdog, normal_interval);
function http_watchdog() {
    if (sh_state === 'crtae') {
        console.log('[sh_state] : ' + sh_state);
        sh_adn.crtae(conf.ae.parent, conf.ae.name, conf.ae.appid, function (status, res_body) {
            console.log(res_body);
            if (status == 2001) {
                ae_response_action(status, res_body, function (status, aeid) {
                    console.log('x-m2m-rsc : ' + status + ' - ' + aeid + ' <----');
                    sh_state = 'rtvae';
                    request_count = 0;
                    return_count = 0;

                    setTimeout(http_watchdog, normal_interval);
                });
            }
            else if (status == 5106 || status == 4105) {
                console.log('x-m2m-rsc : ' + status + ' <----');
                sh_state = 'rtvae';

                setTimeout(http_watchdog, normal_interval);
            }
            else {
                console.log('x-m2m-rsc : ' + status + ' <----');
                setTimeout(http_watchdog, retry_interval);
            }
        });
    }
    else if (sh_state === 'rtvae') {
        if (conf.ae.id === 'S') {
            conf.ae.id = 'S' + shortid.generate();
        }

        console.log('[sh_state] : ' + sh_state);
        sh_adn.rtvae(conf.ae.parent + '/' + conf.ae.name, function (status, res_body) {
            if (status == 2000) {
                var aeid = res_body['m2m:ae']['aei'];
                console.log('x-m2m-rsc : ' + status + ' - ' + aeid + ' <----');

                if(conf.ae.id != aeid && conf.ae.id != ('/'+aeid)) {
                    console.log('AE-ID created is ' + aeid + ' not equal to device AE-ID is ' + conf.ae.id);
                }
                else {
                    sh_state = 'rtvct';
                    request_count = 0;
                    return_count = 0;
                    setTimeout(http_watchdog, normal_interval);
                }
            }
            else {
                console.log('x-m2m-rsc : ' + status + ' <----');
                setTimeout(http_watchdog, retry_interval);
            }
        });
    }
    else if(sh_state === 'rtvct') {
        retrieve_my_cnt_name(function () {
        });
    }
    else if (sh_state === 'crtct') {
        console.log('[sh_state] : ' + sh_state);
        create_cnt_all(request_count, function (status, count) {
            if(status == 9999) {
                setTimeout(http_watchdog, retry_interval);
            }
            else {
                request_count = ++count;
                return_count = 0;
                if (conf.cnt.length <= count) {
                    sh_state = 'delsub';
                    request_count = 0;
                    return_count = 0;

                    setTimeout(http_watchdog, normal_interval);
                }
            }
        });
    }
    else if (sh_state === 'delsub') {
        console.log('[sh_state] : ' + sh_state);
        delete_sub_all(request_count, function (status, count) {
            if(status == 9999) {
                setTimeout(http_watchdog, retry_interval);
            }
            else {
                request_count = ++count;
                return_count = 0;
                if (conf.sub.length <= count) {
                    sh_state = 'crtsub';
                    request_count = 0;
                    return_count = 0;

                    setTimeout(http_watchdog, normal_interval);
                }
            }
        });
    }
    else if (sh_state === 'crtsub') {
        console.log('[sh_state] : ' + sh_state);
        create_sub_all(request_count, function (status, count) {
            if(status == 9999) {
                setTimeout(http_watchdog, retry_interval);
            }
            else {
                request_count = ++count;
                return_count = 0;
                if (conf.sub.length <= count) {
                    sh_state = 'crtci';

                    ready_for_notification();

                    setTimeout(http_watchdog, normal_interval);
                }
            }
        });
    }
    else if (sh_state === 'crtci') {
        send_to_Mobius(my_cnt_name, dry_data_block);

        setTimeout(http_watchdog, data_interval);
    }
}

function send_to_Mobius(url, obj_content) {
    sh_adn.crtci(url+'?rcn=0', 0, obj_content, null, function () {
    });
}

// for notification
//var xmlParser = bodyParser.text({ type: '*/*' });

function mqtt_connect(serverip, noti_topic) {
    if(mqtt_client == null) {
        if (conf.usesecure === 'disable') {
            var connectOptions = {
                host: serverip,
                port: conf.cse.mqttport,
// username: 'keti',
// password: 'keti123',
                protocol: "mqtt",
                keepalive: 10,
// clientId: serverUID,
                protocolId: "MQTT",
                protocolVersion: 4,
                clean: true,
                reconnectPeriod: 2000,
                connectTimeout: 2000,
                rejectUnauthorized: false
            };
        }
        else {
            connectOptions = {
                host: serverip,
                port: conf.cse.mqttport,
                protocol: "mqtts",
                keepalive: 10,
// clientId: serverUID,
                protocolId: "MQTT",
                protocolVersion: 4,
                clean: true,
                reconnectPeriod: 2000,
                connectTimeout: 2000,
                key: fs.readFileSync("./server-key.pem"),
                cert: fs.readFileSync("./server-crt.pem"),
                rejectUnauthorized: false
            };
        }

        mqtt_client = mqtt.connect(connectOptions);
    }

    mqtt_client.on('connect', function () {
        console.log('mqtt connected to ' + serverip);
        for(var idx in noti_topic) {
            if(noti_topic.hasOwnProperty(idx)) {
                mqtt_client.subscribe(noti_topic[idx]);
                console.log('[mqtt_connect] noti_topic[' + idx + ']: ' + noti_topic[idx]);
            }
        }
    });

    mqtt_client.on('message', function (topic, message) {
        if(topic.includes('/oneM2M/req/')) {
            var jsonObj = JSON.parse(message.toString());

            if (jsonObj['m2m:rqp'] == null) {
                jsonObj['m2m:rqp'] = jsonObj;
            }

            noti.mqtt_noti_action(topic.split('/'), jsonObj);
        }
        else {
        }
    });

    mqtt_client.on('error', function (err) {
        console.log(err.message);
    });
}

///////////////////////////////////////////////////////////////////////////////

var dry_mqtt_client = null;
var dry_noti_topic = [];

dry_noti_topic.push('/res_zero_point');
dry_noti_topic.push('/res_calc_factor');
dry_noti_topic.push('/res_internal_temp');
dry_noti_topic.push('/res_input_door');
dry_noti_topic.push('/res_output_door');
dry_noti_topic.push('/res_safe_door');
dry_noti_topic.push('/res_weight');
dry_noti_topic.push('/res_operation_mode');
dry_noti_topic.push('/res_debug_mode');
dry_noti_topic.push('/res_start_btn');

function dry_mqtt_connect(broker_ip, port, noti_topic) {
    if(dry_mqtt_client == null) {
        if (conf.usesecure === 'disable') {
            var connectOptions = {
                host: broker_ip,
                port: port,
// username: 'keti',
// password: 'keti123',
                protocol: "mqtt",
                keepalive: 10,
// clientId: serverUID,
                protocolId: "MQTT",
                protocolVersion: 4,
                clean: true,
                reconnectPeriod: 2000,
                connectTimeout: 2000,
                rejectUnauthorized: false
            };
        }
        else {
            connectOptions = {
                host: broker_ip,
                port: port,
                protocol: "mqtts",
                keepalive: 10,
// clientId: serverUID,
                protocolId: "MQTT",
                protocolVersion: 4,
                clean: true,
                reconnectPeriod: 2000,
                connectTimeout: 2000,
                key: fs.readFileSync("./server-key.pem"),
                cert: fs.readFileSync("./server-crt.pem"),
                rejectUnauthorized: false
            };
        }

        dry_mqtt_client = mqtt.connect(connectOptions);
    }

    dry_mqtt_client.on('connect', function () {
        console.log('msw_mqtt connected to ' + broker_ip);
        for(var idx in noti_topic) {
            if(noti_topic.hasOwnProperty(idx)) {
                dry_mqtt_client.subscribe(noti_topic[idx]);
                console.log('[msw_mqtt_connect] noti_topic[' + idx + ']: ' + noti_topic[idx]);
            }
        }
    });

    dry_mqtt_client.on('message', function (topic, message) {
        try {
            var msg_obj = JSON.parse(message.toString());
        }
        catch (e) {
        }

        //console.log(topic + ' - ' + JSON.stringify(msg_obj));

        if(msg_obj.hasOwnProperty('val2')) {
            func[topic.replace('/', '')](msg_obj.val, msg_obj.val2);
        }
        else {
            func[topic.replace('/', '')](msg_obj.val);
        }
    });

    dry_mqtt_client.on('error', function (err) {
        console.log(err.message);
    });
}

dry_mqtt_connect('localhost', 1883, dry_noti_topic);

///////////////////////////////////////////////////////////////////////////////

var dry_data_block = {};
try {
    dry_data_block = JSON.parse(fs.readFileSync('ddb.json', 'utf8'));
}
catch (e) {
    dry_data_block.state = 'INIT';
    dry_data_block.internal_temp = 0.0;
    dry_data_block.external_temp = 0.0;
    dry_data_block.cur_weight = 0.0;
    dry_data_block.ref_weight = 0.0;
    dry_data_block.pre_weight = 0.0;
    dry_data_block.tar_weight1 = 0.0;
    dry_data_block.tar_weight2 = 0.0;
    dry_data_block.tar_weight3 = 0.0;
    dry_data_block.cum_weight = 0.0;
    dry_data_block.cum_ref_weight = 900;
    dry_data_block.input_door = 0;
    dry_data_block.output_door = 0;
    dry_data_block.safe_door = 0;
    dry_data_block.operation_mode = 0;
    dry_data_block.debug_mode = 0;
    dry_data_block.start_btn = 0;
    dry_data_block.stirrer_mode = 0;
    dry_data_block.elapsed_time = 0;
    dry_data_block.debug_message = 'INIT';
    dry_data_block.loadcell_factor = 1841;
    dry_data_block.loadcell_ref_weight = 20;
    dry_data_block.correlation_value = 4.6;

    fs.writeFileSync('ddb.json', JSON.stringify(dry_data_block, null, 4), 'utf8');
}


var pre_state = 'None';
var pre_cur_weight = -1.0;
var pre_loadcell_factor = -1.0;
var pre_input_door = -1;
var pre_output_door = -1;
var pre_safe_door = -1;
var pre_internal_temp = -1.0;
var pre_elapsed_time = -1;
var pre_debug_message = '';


dry_data_block.input_door = 1;
dry_data_block.output_door = 1;
dry_data_block.safe_door = 1;

dry_data_block.state = 'INIT';
pre_state = '';
print_lcd_state();

dry_data_block.debug_message = 'Initialize';
pre_debug_message = '';
print_lcd_debug_message();


///////////////////////////////////////////////////////////////////////////////
// function of food dryer machine controling, sensing

function print_lcd_state() {
    if(dry_mqtt_client != null) {
        if (pre_state != dry_data_block.state) {
            pre_state = dry_data_block.state;

            var msg_obj = {};
            msg_obj.val = dry_data_block.state;

            dry_mqtt_client.publish('/print_lcd_state', JSON.stringify(msg_obj));
        }
    }
}

function print_lcd_loadcell_factor() {
    if(dry_mqtt_client != null) {
        if (pre_loadcell_factor != dry_data_block.loadcell_factor) {
            pre_loadcell_factor = dry_data_block.loadcell_factor;

            var msg_obj = {};
            msg_obj.val = dry_data_block.loadcell_factor;
            msg_obj.val2 = dry_data_block.loadcell_ref_weight;
            dry_mqtt_client.publish('/print_lcd_loadcell_factor', JSON.stringify(msg_obj));
        }
    }
}

function print_lcd_input_door() {
    if(dry_mqtt_client != null) {
        if (pre_input_door != dry_data_block.input_door) {
            pre_input_door = dry_data_block.input_door;

            var msg_obj = {};
            msg_obj.val = dry_data_block.input_door;
            dry_mqtt_client.publish('/print_lcd_input_door', JSON.stringify(msg_obj));
        }
    }
}

function print_lcd_output_door() {
    if(dry_mqtt_client != null) {
        if (pre_output_door != dry_data_block.output_door) {
            pre_output_door = dry_data_block.output_door;

            var msg_obj = {};
            msg_obj.val = dry_data_block.output_door;
            dry_mqtt_client.publish('/print_lcd_output_door', JSON.stringify(msg_obj));
        }
    }
}

function print_lcd_safe_door() {
    if(dry_mqtt_client != null) {
        if (pre_safe_door != dry_data_block.safe_door) {
            pre_safe_door = dry_data_block.safe_door;

            var msg_obj = {};
            msg_obj.val = dry_data_block.safe_door;
            dry_mqtt_client.publish('/print_lcd_safe_door', JSON.stringify(msg_obj));
        }
    }
}

function print_lcd_elapsed_time() {
    if(dry_mqtt_client != null) {
        if (pre_elapsed_time != dry_data_block.elapsed_time) {
            pre_elapsed_time = dry_data_block.elapsed_time;

            var msg_obj = {};
            msg_obj.val = dry_data_block.elapsed_time;
            dry_mqtt_client.publish('/print_lcd_elapsed_time', JSON.stringify(msg_obj));
        }
    }
}

function print_lcd_debug_message() {
    if(dry_mqtt_client != null) {
        if (pre_debug_message != dry_data_block.debug_message) {
            pre_debug_message = dry_data_block.debug_message;

            var msg_obj = {};
            msg_obj.val = dry_data_block.debug_message;
            dry_mqtt_client.publish('/print_lcd_debug_message', JSON.stringify(msg_obj));
        }
    }
}

function set_solenoid(command) {
    if(dry_mqtt_client != null) {
        var msg_obj = {};
        msg_obj.val = command;
        dry_mqtt_client.publish('/set_solenoid', JSON.stringify(msg_obj));
    }
}

function set_fan(command) {
    if(dry_mqtt_client != null) {
        var msg_obj = {};
        msg_obj.val = command;
        dry_mqtt_client.publish('/set_fan', JSON.stringify(msg_obj));
    }
}

function set_heater(command1, command2, command3) {
    if(dry_mqtt_client != null) {
        var msg_obj = {};
        msg_obj.val = command1;
        msg_obj.val2 = command2;
        msg_obj.val3 = command3;
        dry_mqtt_client.publish('/set_heater', JSON.stringify(msg_obj));
    }
}

function set_stirrer(command) {
    if(dry_mqtt_client != null) {
        var msg_obj = {};
        msg_obj.val = command;
        dry_mqtt_client.publish('/set_stirrer', JSON.stringify(msg_obj));
    }
}

function set_buzzer() {
    if(dry_mqtt_client != null) {
        var msg_obj = {};
        msg_obj.val = 1;
        dry_mqtt_client.publish('/set_buzzer', JSON.stringify(msg_obj));
    }
}

function req_zero_point() {
    if(dry_mqtt_client != null) {
        var msg_obj = {};
        msg_obj.val = dry_data_block.loadcell_ref_weight;
        //console.log(dry_data_block.loadcell_ref_weight)
        dry_mqtt_client.publish('/req_zero_point', JSON.stringify(msg_obj));
    }
}

function req_calc_factor() {
    if(dry_mqtt_client != null) {
        var msg_obj = {};
        msg_obj.val = dry_data_block.loadcell_factor;
        dry_mqtt_client.publish('/req_calc_factor', JSON.stringify(msg_obj));
    }
}


function req_internal_temp() {
    if(dry_mqtt_client != null) {
        var msg_obj = {};
        msg_obj.val = 1;
        dry_mqtt_client.publish('/req_internal_temp', JSON.stringify(msg_obj));
        //console.log(msg_obj.val);
        setTimeout(req_internal_temp, 1000 + parseInt(Math.random() * 100));
    }
    else {
        setTimeout(req_internal_temp, 1000 + parseInt(Math.random() * 1000));
    }
}

function req_input_door() {
    if(dry_mqtt_client != null) {
        var msg_obj = {};
        msg_obj.val = 1;
        dry_mqtt_client.publish('/req_input_door', JSON.stringify(msg_obj));

        setTimeout(req_input_door, 100 + parseInt(Math.random() * 50));
    }
    else {
        setTimeout(req_input_door, 1000 + parseInt(Math.random() * 1000));
    }
}

function req_output_door() {
    if(dry_mqtt_client != null) {
        var msg_obj = {};
        msg_obj.val = 1;
        dry_mqtt_client.publish('/req_output_door', JSON.stringify(msg_obj));

        setTimeout(req_output_door, 100 + parseInt(Math.random() * 50));
    }
    else {
        setTimeout(req_output_door, 1000 + parseInt(Math.random() * 1000));
    }
}

function req_safe_door() {
    if(dry_mqtt_client != null) {
        var msg_obj = {};
        msg_obj.val = 1;
        dry_mqtt_client.publish('/req_safe_door', JSON.stringify(msg_obj));

        setTimeout(req_safe_door, 100 + parseInt(Math.random() * 50));
    }
    else {
        setTimeout(req_safe_door, 1000 + parseInt(Math.random() * 1000));
    }
}

function req_weight() {
    if(dry_mqtt_client != null) {
        var msg_obj = {};

        if(dry_data_block.state == 'INIT') {
        }
        else if(dry_data_block.state == 'DEBUG') {
        }
        else {
            msg_obj.val = 1;
            dry_mqtt_client.publish('/req_weight', JSON.stringify(msg_obj));
        }
        setTimeout(req_weight, 1000 + parseInt(Math.random() * 100));
    }
    else {
        setTimeout(req_weight, 1000 + parseInt(Math.random() * 1000));
    }
}

function req_operation_mode() {
    if(dry_mqtt_client != null) {
        var msg_obj = {};
        msg_obj.val = 1;
        dry_mqtt_client.publish('/req_operation_mode', JSON.stringify(msg_obj));

        setTimeout(req_operation_mode, 100 + parseInt(Math.random() * 50));
    }
    else {
        setTimeout(req_operation_mode, 1000 + parseInt(Math.random() * 1000));
    }
}

function req_debug_mode() {
    if(dry_mqtt_client != null) {
        var msg_obj = {};
        msg_obj.val = 1;
        dry_mqtt_client.publish('/req_debug_mode', JSON.stringify(msg_obj));
        //console.log(msg_obj.val);
        setTimeout(req_debug_mode, 100 + parseInt(Math.random() * 50));
    }
    else {
        setTimeout(req_debug_mode, 1000 + parseInt(Math.random() * 1000));
    }
}

function req_start_btn() {
    if(dry_mqtt_client != null) {
        var msg_obj = {};
        msg_obj.val = 1;
        dry_mqtt_client.publish('/req_start_btn', JSON.stringify(msg_obj));

        setTimeout(req_start_btn, 100 + parseInt(Math.random() * 50));
    }
    else {
        setTimeout(req_start_btn, 1000 + parseInt(Math.random() * 1000));
    }
}

function res_zero_point(val) {
    //dry_data_block.loadcell_factor = parseFloat(val.toString()).toFixed(1);

    debug_mode_state = 'put_on';
}

function res_calc_factor(val, val2) {
    dry_data_block.loadcell_factor = parseFloat(val.toString()).toFixed(1);
    dry_data_block.correlation_value = parseFloat(val2.toString()).toFixed(1);

    debug_mode_state = 'complete';
}


function res_internal_temp(val, val2) {
    dry_data_block.internal_temp = parseFloat(val.toString()).toFixed(1);
    dry_data_block.external_temp = parseFloat(val2.toString()).toFixed(1);

    if (pre_internal_temp != dry_data_block.internal_temp) {
        pre_internal_temp = dry_data_block.internal_temp;

        var msg_obj = {};
        msg_obj.val = dry_data_block.internal_temp;
        msg_obj.val2 = dry_data_block.external_temp;
        dry_mqtt_client.publish('/print_lcd_internal_temp', JSON.stringify(msg_obj));
    }
}

var input_door_close_count = 0;
var input_door_open_count = 0;
function res_input_door(val) {
    var status = parseInt(val.toString());

    if(status == 1) {
        input_door_close_count++;
        input_door_open_count = 0;
        if(input_door_close_count > 2) {
            input_door_close_count = 2;

            if(dry_data_block.input_door == 1) {
                dryer_event |= EVENT_INPUT_DOOR_CLOSE;
            }

            dry_data_block.input_door = 0;
        }
    }
    else {
        input_door_close_count = 0;
        input_door_open_count++;
        if(input_door_open_count > 2) {
            input_door_open_count = 2;

            if(dry_data_block.input_door == 0) {
                dryer_event |= EVENT_INPUT_DOOR_OPEN;
            }

            dry_data_block.input_door = 1;
        }
    }
}

var output_door_close_count = 0;
var output_door_open_count = 0;
function res_output_door(val) {
    var status = parseInt(val.toString());

    if(status == 1) {
        output_door_close_count++;
        output_door_open_count = 0;
        if(output_door_close_count > 2) {
            output_door_close_count = 2;

            if(dry_data_block.output_door == 1) {
                dryer_event |= EVENT_OUTPUT_DOOR_CLOSE;
            }

            dry_data_block.output_door = 0;
        }
    }
    else {
        output_door_close_count = 0;
        output_door_open_count++;
        if(output_door_open_count > 2) {
            output_door_open_count = 2;

            if(dry_data_block.output_door == 0) {
                dryer_event |= EVENT_OUTPUT_DOOR_OPEN;
            }

            dry_data_block.output_door = 1;
        }
    }
}

var safe_door_close_count = 0;
var safe_door_open_count = 0;
function res_safe_door(val) {
    var status = parseInt((val).toString());

    if(status == 1) {
        safe_door_close_count++;
        safe_door_open_count = 0;
        if(safe_door_close_count > 2) {
            safe_door_close_count = 2;

            if(dry_data_block.safe_door == 1) {
                dryer_event |= EVENT_SAFE_DOOR_CLOSE;
            }

            dry_data_block.safe_door = 0;
        }
    }
    else {
        safe_door_close_count = 0;
        safe_door_open_count++;
        if(safe_door_open_count > 2) {
            safe_door_open_count = 2;

            if(dry_data_block.safe_door == 0) {
                dryer_event |= EVENT_SAFE_DOOR_OPEN;
            }

            dry_data_block.safe_door = 1;
        }
    }
}

function res_weight(val) {
    //console.log('weight: ' + val);
    dry_data_block.cur_weight = parseFloat(val.toString()).toFixed(1);

    if (pre_cur_weight != dry_data_block.cur_weight) {
        //console.log(dry_data_block.cur_weight);
        pre_cur_weight = dry_data_block.cur_weight;


        var msg_obj = {};
        msg_obj.val = dry_data_block.cur_weight;
        msg_obj.val2 = dry_data_block.tar_weight3;
        dry_mqtt_client.publish('/print_lcd_loadcell', JSON.stringify(msg_obj));
    }
}

var operation_press_count = 0;
var operation_release_count = 0;
function res_operation_mode(val) {
    var status = parseInt(val.toString());
    //console.log(status);
    if(status == 0) {
        operation_press_count++;
        operation_release_count = 0;
        if(operation_press_count > 2) {
            operation_press_count = 2;
            dry_data_block.operation_mode = 0;
        }
    }
    else {
        operation_press_count = 0;
        operation_release_count++;
        if(operation_release_count > 2) {
            operation_release_count = 2;
            dry_data_block.operation_mode = 1;
        }
    }
}

var debug_press_count = 0;
var debug_release_count = 0;
function res_debug_mode(val) {
    var status = parseInt(val.toString());

    if(status == 0) {
        debug_press_count++;
        debug_release_count = 0;
        if(debug_press_count > 2) {
            debug_press_count = 2;
            dry_data_block.debug_mode = 0;
        }
    }
    else {
        debug_press_count = 0;
        debug_release_count++;
        if(debug_release_count > 2) {
            debug_release_count = 2;
            dry_data_block.debug_mode = 1;
        }
    }
}


var start_press_count = 0;
var start_press_flag = 0;
function res_start_btn(val) {
    var status = parseInt(val.toString());

    if(status == 0) {
        start_press_count++;
        if(start_press_count > 2) {
            start_press_flag = 1;
        }

        if(start_press_count > 64) {
            start_press_flag = 2;
            dry_data_block.start_btn = 2;

            dryer_event |= EVENT_START_BTN_LONG;
        }
    }
    else {
        if(start_press_flag == 1) {
            dry_data_block.start_btn = 1;

            dryer_event |= EVENT_START_BTN_CLICK;
        }
        else if(start_press_flag == 2) {
        }

        start_press_flag = 0;
        start_press_count = 0;
    }
}

///////////////////////////////////////////////////////////////////////////////

var always_tick = 0;
var toggle_command = 0;
setTimeout(always_watchdog, first_interval);

function always_watchdog() {
    //내부온도 70도 이상 순환팬과 열교환기 냉각팬 온
    //내부온도 70도 이하 순환팬과 열교환기 냉각팬 오프
    //내부온도 80도 이상 3분 주기로 솔레노이드밸브 온, 오프 반복
    //내부온도 80도 이하 솔레노이드밸브 오프

    if(parseFloat(dry_data_block.internal_temp) <= 30.0) {
        // 순환팬 오프
        // 열교환기 냉각팬 오프

        set_fan(0);
    }
    else if(parseFloat(dry_data_block.internal_temp) > 30.0) {
        // 순환팬 온
        // 열교환기 냉각팬 온

        set_fan(1);
    }

    if(parseFloat(dry_data_block.internal_temp) <= 30.0) {
        // 솔레노이드밸브 오프

        always_tick = 0;
        set_solenoid(0);
    }
    else if(parseFloat(dry_data_block.internal_temp) > 30.0) {
        // 3분 주기로 솔레노이드밸브 온, 오프 반복

        always_tick++;
        if(always_tick >= always_period_tick) {
            always_tick = 0;

            // 솔레노이드밸브 온 - 오프 토글
            toggle_command = toggle_command ? 0 : 1;
        }

        set_solenoid(toggle_command);
    }

    setTimeout(always_watchdog, always_interval);

    // console.log(toggle_command);
    // console.log('check temp if internal temp is 70 more and 80 less');
}

///////////////////////////////////////////////////////////////////////////////

setTimeout(lcd_display_watchdog, display_interval);

function lcd_display_watchdog() {
    // print current info of dry from dry_data_block to lcd

    if(dry_data_block.state == 'DEBUG') {
        setTimeout(print_lcd_state, parseInt(Math.random() * 10));
        setTimeout(print_lcd_loadcell_factor, parseInt(Math.random() * 10));
        setTimeout(print_lcd_debug_message, parseInt(Math.random() * 10));
    }
    else {
        if (dry_data_block.state == 'HEAT') {
            dry_data_block.elapsed_time++;
        }

        setTimeout(print_lcd_state, parseInt(Math.random() * 10));
        setTimeout(print_lcd_input_door, parseInt(Math.random() * 10));
        setTimeout(print_lcd_output_door, parseInt(Math.random() * 10));
        setTimeout(print_lcd_safe_door, parseInt(Math.random() * 10));
        setTimeout(print_lcd_elapsed_time, 0);
        setTimeout(print_lcd_debug_message, parseInt(Math.random() * 10));
    }

    setTimeout(lcd_display_watchdog, display_interval);
}


///////////////////////////////////////////////////////////////////////////////

var debug_mode_state = 'start';

setTimeout(core_watchdog, 2000);

var input_mode_delay_count = 0;
var contents_delay_count = 0;

function core_watchdog() {
    //console.log(dry_data_block.debug_mode);
    //console.log(dry_data_block.state);
    if(dry_data_block.state == 'INIT') {
        pre_input_door = -1;
        pre_output_door = -1;
        pre_safe_door = -1;

        set_heater(0, 0, 0);
        set_stirrer(0);

        if(dryer_event & EVENT_START_BTN_CLICK) {
            dryer_event &= ~EVENT_START_BTN_CLICK;
        }
        else if(dryer_event & EVENT_START_BTN_LONG) {
            dryer_event &= ~EVENT_START_BTN_LONG;
        }
        else if(dryer_event & EVENT_INPUT_DOOR_OPEN) {
            dryer_event &= ~EVENT_INPUT_DOOR_OPEN;
        }
        else if(dryer_event & EVENT_INPUT_DOOR_CLOSE) {
            dryer_event &= ~EVENT_INPUT_DOOR_CLOSE;
        }
        else if(dryer_event & EVENT_OUTPUT_DOOR_OPEN) {
            dryer_event &= ~EVENT_OUTPUT_DOOR_OPEN;

            dry_data_block.debug_message = 'Close output door';
            pre_debug_message = '';
            print_lcd_debug_message();

            set_buzzer();
        }
        else if(dryer_event & EVENT_OUTPUT_DOOR_CLOSE) {
            dryer_event &= ~EVENT_OUTPUT_DOOR_CLOSE;

            dry_data_block.debug_message = '                    ';
            pre_debug_message = '';
            print_lcd_debug_message();
        }
        else if(dryer_event & EVENT_SAFE_DOOR_OPEN) {
            dryer_event &= ~EVENT_SAFE_DOOR_OPEN;

            dry_data_block.debug_message = 'Close safe door';
            pre_debug_message = '';
            print_lcd_debug_message();
            set_buzzer();
        }
        else if(dryer_event & EVENT_SAFE_DOOR_CLOSE) {
            dryer_event &= ~EVENT_SAFE_DOOR_CLOSE;
            dry_data_block.debug_message = '                    ';
            pre_debug_message = '';
            print_lcd_debug_message();
        }
        else {
            if (dry_data_block.safe_door == 0) {
                if (dry_data_block.output_door == 0) {
                    if (dry_data_block.operation_mode == 1) {
                        if(input_mode_delay_count == 0) {
                            // operation switch가 heat로 선택되어져 있으면
                            dry_data_block.debug_message = 'Choose an INPUT mode';
                            print_lcd_debug_message();
                            pre_debug_message = '';

                            set_buzzer();
                        }

                        input_mode_delay_count++;
                        if(input_mode_delay_count > 40) {
                            input_mode_delay_count = 0;
                        }
                    }
                    else {
                        input_mode_delay_count = 0;
                        contents_delay_count = 0;
                        sh_adn.rtvct(zero_mission_name+'/la', 0, function (rsc, res_body, count) {
                            if (rsc == 2000) {
                                var zero_obj = res_body[Object.keys(res_body)[0]].con;

                                dry_data_block.loadcell_factor = zero_obj.loadcell_factor;
                                dry_data_block.correlation_value = zero_obj.correlation_value;

                                if(dry_mqtt_client != null) {
                                    var msg_obj = {};
                                    msg_obj.val = dry_data_block.loadcell_factor;
                                    msg_obj.val2 = dry_data_block.correlation_value;
                                    dry_mqtt_client.publish('/set_zero_point', JSON.stringify(msg_obj));
                                }
                            }
                        });

                        dry_data_block.debug_message = '                    ';
                        pre_debug_message = '';
                        print_lcd_debug_message();

                        dry_data_block.cur_weight = 0.0;
                        dry_data_block.ref_weight = 0.0;
                        dry_data_block.pre_weight = 0.0;
                        dry_data_block.tar_weight1 = 0.0;
                        dry_data_block.tar_weight2 = 0.0;
                        dry_data_block.tar_weight3 = 0.0;

                        dry_data_block.state = 'INPUT';
                        pre_state = '';
                        print_lcd_state();

                        dry_data_block.elapsed_time = 0;

                        if (dry_data_block.cum_weight > dry_data_block.cum_ref_weight) {
                            dry_data_block.debug_message = 'Replace the catalyst';
                            pre_debug_message = '';
                            print_lcd_debug_message();
                            set_buzzer();
                        }
                    }
                }
                else {
                    if(input_mode_delay_count == 0) {
                        dry_data_block.debug_message = 'Close output door';
                        pre_debug_message = '';
                        print_lcd_debug_message();
                        set_buzzer();
                    }

                    input_mode_delay_count++;
                    if(input_mode_delay_count > 40) {
                        input_mode_delay_count = 0;
                    }

                }
            }
            else {
                if(input_mode_delay_count == 0) {
                    dry_data_block.debug_message = 'Close safe door';
                    pre_debug_message = '';
                    print_lcd_debug_message();
                    set_buzzer();
                }

                input_mode_delay_count++;
                if(input_mode_delay_count > 40) {
                    input_mode_delay_count = 0;
                }
            }
        }

        setTimeout(core_watchdog, normal_interval);
    }

    else if(dry_data_block.state == 'INPUT') {
        set_heater(0, 0, 0);
        set_stirrer(0);

        if(dryer_event & EVENT_START_BTN_CLICK) {
            dryer_event &= ~EVENT_START_BTN_CLICK;

            if (dry_data_block.safe_door == 0) {
                if (dry_data_block.output_door == 0) {
                    if (dry_data_block.input_door == 0) {
                        if (dry_data_block.operation_mode == 1) {
                            // 스위치가 HEAT 모드로 되어 있다면

                            dry_data_block.ref_weight = dry_data_block.ref_weight + dry_data_block.cur_weight - dry_data_block.pre_weight;

                            dry_data_block.tar_weight1 = parseFloat(dry_data_block.ref_weight * 0.60).toFixed(1);
                            dry_data_block.tar_weight2 = parseFloat(dry_data_block.ref_weight * 0.30).toFixed(1);
                            dry_data_block.tar_weight3 = parseFloat(dry_data_block.ref_weight * 0.17).toFixed(1);

                            fs.writeFileSync('ddb.json', JSON.stringify(dry_data_block, null, 4), 'utf8');

                            console.log(dry_data_block.state);
                            dry_data_block.state = 'HEAT';
                            pre_state = '';
                            print_lcd_state();
                            console.log('->' + dry_data_block.state);

                            dry_data_block.debug_message = '                    ';
                            pre_debug_message = '';
                            print_lcd_debug_message();

                            set_heater(1, 1, 1);
                            set_stirrer(1);

                            my_sortie_name = moment().format('YYYY_MM_DD_T_hh_mm');
                            my_cnt_name = my_parent_cnt_name + '/' + my_sortie_name;
                            sh_adn.crtct(my_parent_cnt_name + '?rcn=0', my_sortie_name, 0, function (rsc, res_body, count) {
                            });
                        }
                        else {
                            dry_data_block.debug_message = 'Choose a HEAT mode';
                            pre_debug_message = '';
                            print_lcd_debug_message();
                            set_buzzer();
                        }
                    }
                    else {
                        dry_data_block.debug_message = 'Close input door';
                        pre_debug_message = '';
                        print_lcd_debug_message();
                        set_buzzer();
                    }
                }
                else {
                    dry_data_block.debug_message = 'Close output door';
                    pre_debug_message = '';
                    print_lcd_debug_message();
                    set_buzzer();
                }
            }
            else {
                dry_data_block.debug_message = 'Close safe door';
                pre_debug_message = '';
                print_lcd_debug_message();
                set_buzzer();
            }
        }
        else if(dryer_event & EVENT_START_BTN_LONG) {
            dryer_event &= ~EVENT_START_BTN_LONG;
        }
        else if(dryer_event & EVENT_INPUT_DOOR_OPEN) {
            dryer_event &= ~EVENT_INPUT_DOOR_OPEN;
        }
        else if(dryer_event & EVENT_INPUT_DOOR_CLOSE) {
            dryer_event &= ~EVENT_INPUT_DOOR_CLOSE;
        }
        else if(dryer_event & EVENT_OUTPUT_DOOR_OPEN) {
            dryer_event &= ~EVENT_OUTPUT_DOOR_OPEN;

            dry_data_block.debug_message = 'Close output door';
            pre_debug_message = '';
            print_lcd_debug_message();
            set_buzzer();
        }
        else if(dryer_event & EVENT_OUTPUT_DOOR_CLOSE) {
            dryer_event &= ~EVENT_OUTPUT_DOOR_CLOSE;

            dry_data_block.debug_message = '                    ';
            pre_debug_message = '';
            print_lcd_debug_message();
        }
        else if(dryer_event & EVENT_SAFE_DOOR_OPEN) {
            dryer_event &= ~EVENT_SAFE_DOOR_OPEN;

            dry_data_block.debug_message = 'Close safe door';
            pre_debug_message = '';
            print_lcd_debug_message();
            set_buzzer();
        }
        else if(dryer_event & EVENT_SAFE_DOOR_CLOSE) {
            dryer_event &= ~EVENT_SAFE_DOOR_CLOSE;

            dry_data_block.debug_message = '                    ';
            pre_debug_message = '';
            print_lcd_debug_message();
        }
        else {
            if (dry_data_block.debug_mode == 1) {
                debug_mode_state = 'start';

                console.log(dry_data_block.state);
                dry_data_block.state = 'DEBUG';
                pre_state = '';
                print_lcd_state();
                console.log('->' + dry_data_block.state);

                set_buzzer();
            }
            else {
            }
        }

        setTimeout(core_watchdog, normal_interval);
    }

    else if(dry_data_block.state == 'HEAT') {
        if(dryer_event & EVENT_START_BTN_CLICK) {
            dryer_event &= ~EVENT_START_BTN_CLICK;
        }
        else if(dryer_event & EVENT_START_BTN_LONG) {
            dryer_event &= ~EVENT_START_BTN_LONG;
        }
        else if(dryer_event & EVENT_INPUT_DOOR_OPEN) {
            dryer_event &= ~EVENT_INPUT_DOOR_OPEN;

            dry_data_block.debug_message = 'Exception';
            pre_debug_message = '';
            print_lcd_debug_message();

            dry_data_block.state = 'EXCEPTION';
            pre_state = '';
            print_lcd_state();

            set_heater(0, 0, 0);
            set_stirrer(0);

            set_buzzer();

            input_mode_delay_count = 0;
            contents_delay_count = 0;
        }
        else if(dryer_event & EVENT_INPUT_DOOR_CLOSE) {
            dryer_event &= ~EVENT_INPUT_DOOR_CLOSE;
        }
        else if(dryer_event & EVENT_OUTPUT_DOOR_OPEN) {
            dryer_event &= ~EVENT_OUTPUT_DOOR_OPEN;

            dry_data_block.debug_message = 'Exception';
            pre_debug_message = '';
            print_lcd_debug_message();

            dry_data_block.state = 'EXCEPTION';
            pre_state = '';
            print_lcd_state();

            set_heater(0, 0, 0);
            set_stirrer(0);

            set_buzzer();

            input_mode_delay_count = 0;
            contents_delay_count = 0;
        }
        else if(dryer_event & EVENT_OUTPUT_DOOR_CLOSE) {
            dryer_event &= ~EVENT_OUTPUT_DOOR_CLOSE;
        }
        else if(dryer_event & EVENT_SAFE_DOOR_OPEN) {
            dryer_event &= ~EVENT_SAFE_DOOR_OPEN;

            dry_data_block.debug_message = 'Exception';
            pre_debug_message = '';
            print_lcd_debug_message();

            dry_data_block.state = 'EXCEPTION';
            pre_state = '';
            print_lcd_state();

            set_heater(0, 0, 0);
            set_stirrer(0);

            set_buzzer();

            input_mode_delay_count = 0;
            contents_delay_count = 0;
        }
        else if(dryer_event & EVENT_SAFE_DOOR_CLOSE) {
            dryer_event &= ~EVENT_SAFE_DOOR_CLOSE;
        }
        else {
            if (dry_data_block.operation_mode == 0) {
                dry_data_block.pre_weight = dry_data_block.cur_weight;

                fs.writeFileSync('ddb.json', JSON.stringify(dry_data_block, null, 4), 'utf8');

                dry_data_block.state = 'INPUT';
                pre_state = '';
                print_lcd_state();

                set_heater(0, 0, 0);
                set_stirrer(0);

                set_buzzer();
            }
            else {
                if(parseFloat(dry_data_block.external_temp) < 185.0) {
                    if (parseFloat(dry_data_block.cur_weight) <= parseFloat(dry_data_block.tar_weight3)) {
                        dry_data_block.cum_weight += dry_data_block.ref_weight;

                        //console.log('heater 0');

                        dry_data_block.ref_weight = 0.0;
                        dry_data_block.pre_weight = 0.0;
                        dry_data_block.tar_weight1 = 0.0;
                        dry_data_block.tar_weight2 = 0.0;
                        dry_data_block.tar_weight3 = 0.0;

                        fs.writeFileSync('ddb.json', JSON.stringify(dry_data_block, null, 4), 'utf8');

                        dry_data_block.state = 'END';
                        pre_state = '';
                        print_lcd_state();

                        input_mode_delay_count = 0;
                        contents_delay_count = 0;

                        set_heater(0, 0, 0);
                        set_stirrer(0);

                        set_buzzer();

                        my_sortie_name = 'disarm';
                        my_cnt_name = my_parent_cnt_name + '/' + my_sortie_name;
                    }
                    else if (parseFloat(dry_data_block.cur_weight) <= parseFloat(dry_data_block.tar_weight2)) {
                        //console.log('heater1 ' + dry_data_block.cur_weight + ' ' + dry_data_block.tar_weight1 + ' ' + dry_data_block.tar_weight2 + ' ' + dry_data_block.tar_weight3);
                        set_heater(1, 0, 0);
                        set_stirrer(1);
                    }
                    else if (parseFloat(dry_data_block.cur_weight) <= parseFloat(dry_data_block.tar_weight1)) {
                        //console.log('heater2 ' + dry_data_block.cur_weight + ' ' + dry_data_block.tar_weight1 + ' ' + dry_data_block.tar_weight2 + ' ' + dry_data_block.tar_weight3);
                        set_heater(1, 1, 0);
                        set_stirrer(1);
                    }
                    else {
                        //console.log('heater3 ' + dry_data_block.cur_weight + ' ' + dry_data_block.tar_weight1 + ' ' + dry_data_block.tar_weight2 + ' ' + dry_data_block.tar_weight3);
                        set_heater(1, 1, 1);
                        set_stirrer(1);
                    }
                }
                else {
                    set_heater(0, 0, 0);
                    set_stirrer(1);
                }
            }
        }

        setTimeout(core_watchdog, normal_interval);
    }

    else if(dry_data_block.state == 'END') {
        if(dryer_event & EVENT_START_BTN_CLICK) {
            dryer_event &= ~EVENT_START_BTN_CLICK;
        }
        else if(dryer_event & EVENT_START_BTN_LONG) {
            dryer_event &= ~EVENT_START_BTN_LONG;
        }
        else if(dryer_event & EVENT_INPUT_DOOR_OPEN) {
            dryer_event &= ~EVENT_INPUT_DOOR_OPEN;
        }
        else if(dryer_event & EVENT_INPUT_DOOR_CLOSE) {
            dryer_event &= ~EVENT_INPUT_DOOR_CLOSE;
        }
        else if(dryer_event & EVENT_OUTPUT_DOOR_OPEN) {
            dryer_event &= ~EVENT_OUTPUT_DOOR_OPEN;

            set_stirrer(1);
        }
        else if(dryer_event & EVENT_OUTPUT_DOOR_CLOSE) {
            dryer_event &= ~EVENT_OUTPUT_DOOR_CLOSE;

            set_stirrer(0);
        }
        else if(dryer_event & EVENT_SAFE_DOOR_OPEN) {
            dryer_event &= ~EVENT_SAFE_DOOR_OPEN;
        }
        else if(dryer_event & EVENT_SAFE_DOOR_CLOSE) {
            dryer_event &= ~EVENT_SAFE_DOOR_CLOSE;
        }
        else {
            if (dry_data_block.cur_weight < 0.5) {
                set_heater(0, 0, 0);
                set_stirrer(0);

                if (dry_data_block.operation_mode == 0) {

                    set_buzzer();

                    dry_data_block.state = 'INIT';
                    pre_state = '';
                    print_lcd_state();

                    dry_data_block.elapsed_time = 0;

                    // 스위치가 INPUT 모드로 되어 있다면
                    set_heater(0, 0, 0);
                    set_stirrer(0);
                }
                else {
                    if(input_mode_delay_count == 0) {
                        // operation switch가 heat로 선택되어져 있으면
                        dry_data_block.debug_message = 'Choose an INPUT mode';
                        //print_lcd_debug_message();
                        //pre_debug_message = '';

                        set_buzzer();
                    }

                    input_mode_delay_count++;
                    if(input_mode_delay_count > 40) {
                        input_mode_delay_count = 0;
                    }
                }
            }
            else {
                if(contents_delay_count == 0) {
                    dry_data_block.debug_message = 'Empty the contents';
                    pre_debug_message = '';
                    print_lcd_debug_message();
                }

                contents_delay_count++;
                if(contents_delay_count > 40) {
                    contents_delay_count = 0;
                }
            }
        }

        setTimeout(core_watchdog, normal_interval);
    }

    else if(dry_data_block.state == 'DEBUG') {
        if(dryer_event & EVENT_START_BTN_CLICK) {
            dryer_event &= ~EVENT_START_BTN_CLICK;

            if(debug_mode_state == 'put_on_waiting') {

                dry_data_block.debug_message = 'Calculating';
                pre_debug_message = '';
                print_lcd_debug_message();

                req_calc_factor();
            }
        }
        else if(dryer_event & EVENT_START_BTN_LONG) {
            dryer_event &= ~EVENT_START_BTN_LONG;
        }
        else if(dryer_event & EVENT_INPUT_DOOR_OPEN) {
            dryer_event &= ~EVENT_INPUT_DOOR_OPEN;
        }
        else if(dryer_event & EVENT_INPUT_DOOR_CLOSE) {
            dryer_event &= ~EVENT_INPUT_DOOR_CLOSE;
        }
        else if(dryer_event & EVENT_OUTPUT_DOOR_OPEN) {
            dryer_event &= ~EVENT_OUTPUT_DOOR_OPEN;
        }
        else if(dryer_event & EVENT_OUTPUT_DOOR_CLOSE) {
            dryer_event &= ~EVENT_OUTPUT_DOOR_CLOSE;
        }
        else if(dryer_event & EVENT_SAFE_DOOR_OPEN) {
            dryer_event &= ~EVENT_SAFE_DOOR_OPEN;
        }
        else if(dryer_event & EVENT_SAFE_DOOR_CLOSE) {
            dryer_event &= ~EVENT_SAFE_DOOR_CLOSE;
        }
        else {
            if (dry_data_block.debug_mode == 0) {
                set_heater(0, 0, 0);
                set_stirrer(0);

                set_buzzer();

                console.log(dry_data_block.state);
                dry_data_block.state = 'INIT';
                pre_state = '';
                print_lcd_state();
                console.log('->' + dry_data_block.state);

                dry_data_block.debug_message = '                    ';
                pre_debug_message = '';
                print_lcd_debug_message();

                dry_data_block.elapsed_time = 0;

                pre_cur_weight = 9999;
            }
            else {
                if (debug_mode_state == 'start') {
                    console.log("Start zero point");

                    dry_data_block.debug_message = 'Start zero point';
                    pre_debug_message = '';
                    print_lcd_debug_message();

                    req_zero_point();

                    debug_mode_state = 'start_waiting';

                    setTimeout(core_watchdog, normal_interval);
                }
                else if (debug_mode_state == 'put_on') {
                    dry_data_block.debug_message = 'Put weight on - ' + dry_data_block.loadcell_ref_weight;
                    pre_debug_message = '';
                    print_lcd_debug_message();

                    debug_mode_state = 'put_on_waiting';

                    setTimeout(core_watchdog, normal_interval);
                }
                else if (debug_mode_state == 'complete') {
                    dry_data_block.debug_message = 'Complete zero point';
                    pre_debug_message = '';
                    print_lcd_debug_message();

                    debug_mode_state = 'completed';

                    var obj = {};
                    obj.loadcell_factor = dry_data_block.loadcell_factor;
                    obj.correlation_value = dry_data_block.correlation_value;
                    send_to_Mobius(zero_mission_name, obj);
                }
                else {
                }
            }
        }

        setTimeout(core_watchdog, normal_interval);
    }

    else if(dry_data_block.state == 'EXCEPTION') {
        if(dryer_event & EVENT_START_BTN_CLICK) {
            dryer_event &= ~EVENT_START_BTN_CLICK;
        }
        else if(dryer_event & EVENT_START_BTN_LONG) {
            dryer_event &= ~EVENT_START_BTN_LONG;
        }
        else if(dryer_event & EVENT_INPUT_DOOR_OPEN) {
            dryer_event &= ~EVENT_INPUT_DOOR_OPEN;

            dry_data_block.debug_message = 'Close input door';
            pre_debug_message = '';
            print_lcd_debug_message();
            set_buzzer();
        }
        else if(dryer_event & EVENT_INPUT_DOOR_CLOSE) {
            dryer_event &= ~EVENT_INPUT_DOOR_CLOSE;

            dry_data_block.debug_message = '                    ';
            pre_debug_message = '';
            print_lcd_debug_message();
        }
        else if(dryer_event & EVENT_OUTPUT_DOOR_OPEN) {
            dryer_event &= ~EVENT_OUTPUT_DOOR_OPEN;

            dry_data_block.debug_message = 'Close output door';
            pre_debug_message = '';
            print_lcd_debug_message();
            set_buzzer();
        }
        else if(dryer_event & EVENT_OUTPUT_DOOR_CLOSE) {
            dryer_event &= ~EVENT_OUTPUT_DOOR_CLOSE;

            dry_data_block.debug_message = '                    ';
            pre_debug_message = '';
            print_lcd_debug_message();
        }
        else if(dryer_event & EVENT_SAFE_DOOR_OPEN) {
            dryer_event &= ~EVENT_SAFE_DOOR_OPEN;

            dry_data_block.debug_message = 'Close safe door';
            pre_debug_message = '';
            print_lcd_debug_message();
            set_buzzer();
        }
        else if(dryer_event & EVENT_SAFE_DOOR_CLOSE) {
            dryer_event &= ~EVENT_SAFE_DOOR_CLOSE;

            dry_data_block.debug_message = '                    ';
            pre_debug_message = '';
            print_lcd_debug_message();
        }
        else {
            if (dry_data_block.operation_mode == 1) {
                if(input_mode_delay_count == 0) {
                    dry_data_block.debug_message = 'Choose an INPUT mode';
                    pre_debug_message = '';
                    print_lcd_debug_message();
                    set_buzzer();
                }

                input_mode_delay_count++;
                if(input_mode_delay_count > 40) {
                    input_mode_delay_count = 0;
                }
            }
            else {
                dry_data_block.pre_weight = dry_data_block.cur_weight;

                fs.writeFileSync('ddb.json', JSON.stringify(dry_data_block, null, 4), 'utf8');

                dry_data_block.state = 'INPUT';
                pre_state = '';
                print_lcd_state();

                set_heater(0, 0, 0);
                set_stirrer(0);

                set_buzzer();
            }
        }

        setTimeout(core_watchdog, normal_interval);
    }

    else {
        setTimeout(core_watchdog, normal_interval);
    }

    //console.log('core watchdog');
}

///////////////////////////////////////////////////////////////////////////////

setTimeout(food_watchdog, 1000);

function food_watchdog(){
    //100ms동작
    //실시간으로 변경되는상태값 저장
    //roadcell_lunch() //roadcell측정

    setTimeout(req_internal_temp, parseInt(Math.random()*10));
    setTimeout(req_input_door, parseInt(Math.random()*10));
    setTimeout(req_output_door, parseInt(Math.random()*10));
    setTimeout(req_safe_door, parseInt(Math.random()*10));
    setTimeout(req_weight, parseInt(Math.random()*10));
    setTimeout(req_operation_mode, parseInt(Math.random()*10));
    setTimeout(req_debug_mode, parseInt(Math.random()*10));
    setTimeout(req_start_btn, parseInt(Math.random()*10));

    //console.log('food watchdog');
}

var func = {};
func['res_zero_point'] = res_zero_point;
func['res_calc_factor'] = res_calc_factor;
func['res_internal_temp'] = res_internal_temp;
func['res_input_door'] = res_input_door;
func['res_output_door'] = res_output_door;
func['res_safe_door'] = res_safe_door;
func['res_weight'] = res_weight;
func['res_operation_mode'] = res_operation_mode;
func['res_debug_mode'] = res_debug_mode;
func['res_start_btn'] = res_start_btn;
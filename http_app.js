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
// var moment = require('moment');

const { exec } = require("child_process");

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
global.lte_parent_mission_name = '';
global.lte_mission_name = '';
global.my_sortie_name = 'disarm';
// global.my_drone_type = 'pixhawk';
global.my_secure = 'off';

const first_interval = 3000;
const retry_interval = 2500;
const normal_interval = 100;
const data_interval = 2000;
const display_interval = 1000;
const food_interval = 200;

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
        mqtt_connect(conf.cse.host, noti_topic);
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
        //     // console.log(drone_info);

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
            my_cnt_name = my_parent_cnt_name + '/' + info.name; // /Mobius/KETI_DRY/Dry_Data/keti/

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

            lte_parent_mission_name = info.parent + '/' + info.name;
            lte_mission_name = lte_parent_mission_name + '/' + my_sortie_name;

            info.parent = lte_parent_mission_name;
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
        send_to_Mobius();
    }
}

function send_to_Mobius() {
    sh_adn.crtci(my_cnt_name+'?rcn=0', 0, dry_data_block, null, function () {

    });

    setTimeout(http_watchdog, data_interval);
}

// for notification
//var xmlParser = bodyParser.text({ type: '*/*' });

function mqtt_connect(serverip, noti_topic) {
    if(mqtt_client == null) {
        if (conf.usesecure === 'disable') {
            var connectOptions = {
                host: serverip,
                port: conf.cse.mqttport,
//              username: 'keti',
//              password: 'keti123',
                protocol: "mqtt",
                keepalive: 10,
//              clientId: serverUID,
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
//              clientId: serverUID,
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

var dry_data_block = {};
try {
    dry_data_block = JSON.parse(fs.readFileSync('ddb.json', 'utf8'));
}
catch (e) {
    dry_data_block.state = 'init';
    dry_data_block.internal_temp = 0.0;
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
    dry_data_block.debug_message = 'init';
    dry_data_block.loadcell_factor = 1517;
    dry_data_block.loadcell_ref_weight = 10.0;

    fs.writeFileSync('ddb.json', JSON.stringify(dry_data_block, null, 4), 'utf8');
}

dry_data_block.state = 'init';
dry_data_block.debug_message = 'initialize';


///////////////////////////////////////////////////////////////////////////////
// function of food dryer machine controling, sensing

function print_lcd_state() {
    exec('phython3 print_lcd_state ' + dry_data_block.state, function(error, stdout, stderr) {
        if (error) {
            console.log(`print_lcd_state() error: ${error.message}`);
            return;
        }

        if (stderr) {
            console.log(`print_lcd_state() stderr: ${stderr}`);
            return;
        }

        console.log(`print_lcd_state() stdout: ${stdout}`);
    });
}

function print_lcd_loadcell() {
    exec('phython3 print_lcd_loadcell ' + dry_data_block.cur_weight + ' ' + dry_data_block.tar_weight3, function(error, stdout, stderr) {
        if (error) {
            console.log(`print_lcd_loadcell() error: ${error.message}`);
            return;
        }

        if (stderr) {
            console.log(`print_lcd_loadcell() stderr: ${stderr}`);
            return;
        }

        console.log(`print_lcd_loadcell() stdout: ${stdout}`);
    });
}

function print_lcd_input_door() {
    exec('phython3 print_lcd_input_door ' + dry_data_block.input_door, function(error, stdout, stderr) {
        if (error) {
            console.log(`print_lcd_input_door() error: ${error.message}`);
            return;
        }

        if (stderr) {
            console.log(`print_lcd_input_door() stderr: ${stderr}`);
            return;
        }

        console.log(`print_lcd_input_door() stdout: ${stdout}`);
    });
}

function print_lcd_output_door() {
    exec('phython3 print_lcd_output_door ' + dry_data_block.output_door, function(error, stdout, stderr) {
        if (error) {
            console.log(`print_lcd_output_door() error: ${error.message}`);
            return;
        }

        if (stderr) {
            console.log(`print_lcd_output_door() stderr: ${stderr}`);
            return;
        }

        console.log(`print_lcd_output_door() stdout: ${stdout}`);
    });
}

function print_lcd_safe_door() {
    exec('phython3 print_lcd_safe_door ' + dry_data_block.safe_door, function(error, stdout, stderr) {
        if (error) {
            console.log(`print_lcd_safe_door() error: ${error.message}`);
            return;
        }

        if (stderr) {
            console.log(`print_lcd_safe_door() stderr: ${stderr}`);
            return;
        }

        console.log(`print_lcd_safe_door() stdout: ${stdout}`);
    });
}

function print_lcd_internal_temp() {
    exec('phython3 print_lcd_internal_temp ' + dry_data_block.internal_temp, function(error, stdout, stderr) {
        if (error) {
            console.log(`print_lcd_internal_temp() error: ${error.message}`);
            return;
        }

        if (stderr) {
            console.log(`print_lcd_internal_temp() stderr: ${stderr}`);
            return;
        }

        console.log(`print_lcd_internal_temp() stdout: ${stdout}`);
    });
}

function print_lcd_elapsed_time() {
    exec('phython3 print_lcd_elapsed_time ' + dry_data_block.elapsed_time, function(error, stdout, stderr) {
        if (error) {
            console.log(`print_lcd_elapsed_time() error: ${error.message}`);
            return;
        }

        if (stderr) {
            console.log(`print_lcd_elapsed_time() stderr: ${stderr}`);
            return;
        }

        console.log(`print_lcd_elapsed_time() stdout: ${stdout}`);
    });
}

function set_solenoid(command) {
    exec('phython3 write_digital_pin ' + solenoid_pin + ' ' + command, function(error, stdout, stderr) {
        if (error) {
            console.log(`set_solenoid() error: ${error.message}`);
            return;
        }

        if (stderr) {
            console.log(`set_solenoid() stderr: ${stderr}`);
            return;
        }

        console.log(`set_solenoid() stdout: ${stdout}`);
    });
}

function set_fan(command) {
    exec('phython3 write_digital_pin ' + fan_pin + ' ' + command, function(error, stdout, stderr) {
        if (error) {
            console.log(`set_fan() error: ${error.message}`);
            return;
        }

        if (stderr) {
            console.log(`set_fan() stderr: ${stderr}`);
            return;
        }

        console.log(`set_fan() stdout: ${stdout}`);
    });
}

function set_heater(command1, command2, command3) {
    exec('phython3 write_digital_pin ' + heater1_pin + ' ' + command1, function(error, stdout, stderr) {
        if (error) {
            console.log(`set_heater1() error: ${error.message}`);
            return;
        }

        if (stderr) {
            console.log(`set_heater1() stderr: ${stderr}`);
            return;
        }

        console.log(`set_heater1() stdout: ${stdout}`);
    });

    exec('phython3 write_digital_pin ' + heater2_pin + ' ' + command2, function(error, stdout, stderr) {
        if (error) {
            console.log(`set_heater2() error: ${error.message}`);
            return;
        }

        if (stderr) {
            console.log(`set_heater2() stderr: ${stderr}`);
            return;
        }

        console.log(`set_heater2() stdout: ${stdout}`);
    });

    exec('phython3 write_digital_pin ' + heater3_pin + ' ' + command3, function(error, stdout, stderr) {
        if (error) {
            console.log(`set_heater3() error: ${error.message}`);
            return;
        }

        if (stderr) {
            console.log(`set_heater3() stderr: ${stderr}`);
            return;
        }

        console.log(`set_heater3() stdout: ${stdout}`);
    });
}

function set_stirrer(command) {
    exec('phython3 write_digital_pin ' + stirrer_pin + ' ' + command, function(error, stdout, stderr) {
        if (error) {
            console.log(`set_stirrer() error: ${error.message}`);
            return;
        }

        if (stderr) {
            console.log(`set_stirrer() stderr: ${stderr}`);
            return;
        }

        console.log(`set_stirrer() stdout: ${stdout}`);
    });
}

function set_zero_point() {
    exec('phython3 set_zero_point ' + dry_data_block.loadcell_ref_weight, function(error, stdout, stderr) {
        if (error) {
            console.log(`set_zero_point() error: ${error.message}`);
            return;
        }

        if (stderr) {
            console.log(`set_zero_point() stderr: ${stderr}`);
            return;
        }

        console.log(`set_zero_point() stdout: ${stdout}`);

        dry_data_block.loadcell_factor = parseInt(stdout.toString());
    });
}

function set_buzzer() {
    exec('phython3 set_buzzer ', function(error, stdout, stderr) {
        if (error) {
            console.log(`set_buzzer() error: ${error.message}`);
            return;
        }

        if (stderr) {
            console.log(`set_buzzer() stderr: ${stderr}`);
            return;
        }

        console.log(`set_buzzer() stdout: ${stdout}`);
    });
}

function get_internal_temp() {
    exec('phython3 read_internal_temp ', function(error, stdout, stderr) {
        if (error) {
            console.log(`get_internal_temp() error: ${error.message}`);
            return;
        }

        if (stderr) {
            console.log(`get_internal_temp() stderr: ${stderr}`);
            return;
        }

        console.log(`get_internal_temp() stdout: ${stdout}`);

        dry_data_block.internal_temp = parseFloat(stdout.toString()).toFixed(1);
    });
}

var input_door_close_count = 0;
var input_door_open_count = 0;
function get_input_door() {
    exec('phython3 read_digital_pin ' + input_door_pin, function(error, stdout, stderr) {
        if (error) {
            console.log(`get_input_door() error: ${error.message}`);
            return;
        }

        if (stderr) {
            console.log(`get_input_door() stderr: ${stderr}`);
            return;
        }

        console.log(`get_input_door() stdout: ${stdout}`);

        var status = parseInt(stdout.toString());

        if(status == 0) {
            input_door_close_count++;
            input_door_open_count = 0;
            if(input_door_close_count > 2) {
                input_door_close_count = 2;
                dry_data_block.input_door = 0;
            }
        }
        else {
            input_door_close_count = 0;
            input_door_open_count++;
            if(input_door_open_count > 2) {
                input_door_open_count = 2;
                dry_data_block.input_door = 1;
            }
        }
    });
}

var output_door_close_count = 0;
var output_door_open_count = 0;
function get_output_door() {
    exec('phython3 read_digital_pin ' + output_door_pin, function(error, stdout, stderr) {
        if (error) {
            console.log(`get_output_door() error: ${error.message}`);
            return;
        }

        if (stderr) {
            console.log(`get_output_door() stderr: ${stderr}`);
            return;
        }

        console.log(`get_output_door() stdout: ${stdout}`);

        var status = parseInt(stdout.toString());

        if(status == 0) {
            output_door_close_count++;
            output_door_open_count = 0;
            if(output_door_close_count > 2) {
                output_door_close_count = 2;
                dry_data_block.output_door = 0;
            }
        }
        else {
            output_door_close_count = 0;
            output_door_open_count++;
            if(output_door_open_count > 2) {
                output_door_open_count = 2;
                dry_data_block.output_door = 1;
            }
        }
    });
}

var safe_door_close_count = 0;
var safe_door_open_count = 0;
function get_safe_door() {
    exec('phython3 read_digital_pin ' + safe_door_pin, function(error, stdout, stderr) {
        if (error) {
            console.log(`get_safe_door() error: ${error.message}`);
            return;
        }

        if (stderr) {
            console.log(`get_safe_door() stderr: ${stderr}`);
            return;
        }

        console.log(`get_safe_door() stdout: ${stdout}`);

        var status = parseInt((stdout).toString());

        if(status == 0) {
            safe_door_close_count++;
            safe_door_open_count = 0;
            if(safe_door_close_count > 2) {
                safe_door_close_count = 2;
                dry_data_block.safe_door = 0;
            }
        }
        else {
            safe_door_close_count = 0;
            safe_door_open_count++;
            if(safe_door_open_count > 2) {
                safe_door_open_count = 2;
                dry_data_block.safe_door = 1;
            }
        }
    });
}

function get_weight() {
    exec('phython3 read_weight ' + dry_data_block.loadcell_factor, function(error, stdout, stderr) {
        if (error) {
            console.log(`get_weight() error: ${error.message}`);
            return;
        }

        if (stderr) {
            console.log(`get_weight() stderr: ${stderr}`);
            return;
        }

        console.log(`get_weight() stdout: ${stdout}`);

        dry_data_block.cur_weight = parseFloat(stdout.toString()).toFixed(1);
    });
}

var operation_press_count = 0;
var operation_release_count = 0;
function get_operation_mode() {
    exec('phython3 read_digital_pin ' + operation_pin, function(error, stdout, stderr) {
        if (error) {
            console.log(`get_operation_mode() error: ${error.message}`);
            return;
        }
        if (stderr) {
            console.log(`get_operation_mode() stderr: ${stderr}`);
            return;
        }

        console.log(`get_operation_mode() stdout: ${stdout}`);

        var status = parseInt(stdout.toString());

        if(status == 0) {
            operation_press_count++;
            operation_release_count = 0;
            if(operation_press_count > 2) {
                operation_press_count = 2;
                dry_data_block.operation_mode = 1;
            }
        }
        else {
            operation_press_count = 0;
            operation_release_count++;
            if(operation_release_count > 2) {
                operation_release_count = 2;
                dry_data_block.operation_mode = 0;
            }
        }
    });
}

var debug_press_count = 0;
var debug_release_count = 0;
function get_debug_mode() {
    exec('phython3 read_digital_pin ' + debug_pin, function(error, stdout, stderr) {
        if (error) {
            console.log(`get_debug_mode() error: ${error.message}`);
            return;
        }
        if (stderr) {
            console.log(`get_debug_mode() stderr: ${stderr}`);
            return;
        }

        console.log(`get_debug_mode() stdout: ${stdout}`);

        var status = parseInt(stdout.toString());

        if(status == 0) {
            debug_press_count++;
            debug_release_count = 0;
            if(debug_press_count > 2) {
                debug_press_count = 2;
                dry_data_block.debug_mode = 1;
            }
        }
        else {
            debug_press_count = 0;
            debug_release_count++;
            if(debug_release_count > 2) {
                debug_release_count = 2;
                dry_data_block.debug_mode = 0;
            }
        }
    });
}


var start_press_count = 0;
var start_press_flag = 0;
function get_start_btn() {
    exec('phython3 read_digital_pin ' + start_btn_pin, function(error, stdout, stderr) {
        if (error) {
            console.log(`get_start_btn() error: ${error.message}`);
            return;
        }
        if (stderr) {
            console.log(`get_start_btn() stderr: ${stderr}`);
            return;
        }

        console.log(`get_start_btn() stdout: ${stdout}`);

        var status = parseInt(stdout.toString());

        if(status == 0) {
            start_press_count++;
            if(start_press_count > 2) {
                start_press_flag = 1;
            }

            if(start_press_count > 15) {
                start_press_flag = 2;
                dry_data_block.start_btn = 2;
            }
        }
        else {
            if(start_press_flag == 1) {
                dry_data_block.start_btn = 1;
            }
            else if(start_press_flag == 2) {
            }

            start_press_flag = 0;
            debug_press_count = 0;
        }
    });
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

    if(dry_data_block.internal_temp <= 70.0) {
        // 순환팬 오프
        // 열교환기 냉각팬 오프

        set_fan(0);
    }
    else if(dry_data_block.internal_temp > 70.0) {
        // 순환팬 온
        // 열교환기 냉각팬 온

        set_fan(1);
    }

    if(dry_data_block.internal_temp <= 80.0) {
        // 솔레노이드밸브 오프

        always_tick = 0;
        set_solenoid(0);
    }
    else if(dry_data_block.internal_temp > 80.0) {
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

    if(dry_data_block.state == 'debug') {

    }
    else {
        if (dry_data_block.state == 'heat') {
            dry_data_block.elapsed_time++;
        }

        setTimeout(print_lcd_state, parseInt(Math.random() * 10));
        setTimeout(print_lcd_loadcell, parseInt(Math.random() * 10));
        setTimeout(print_lcd_input_door, parseInt(Math.random() * 10));
        setTimeout(print_lcd_output_door, parseInt(Math.random() * 10));
        setTimeout(print_lcd_safe_door, parseInt(Math.random() * 10));
        setTimeout(print_lcd_internal_temp, parseInt(Math.random() * 10));
        setTimeout(print_lcd_elapsed_time, parseInt(Math.random() * 10));

    }

    setTimeout(lcd_display_watchdog, display_interval);

    console.log('lcd_display_watchdog');
}


///////////////////////////////////////////////////////////////////////////////

setTimeout(core_watchdog, first_interval);

var core_interval = normal_interval;
function core_watchdog() {
    core_interval = normal_interval;

    if(dry_data_block.state == 'init') {
        //히터오프
        //교반기오프
        //음식물 무게 측정
        // 목표 중량 계산?food에서 ? 여기에서 ?

        set_heater(0, 0, 0);
        set_stirrer(0);

        if(dry_data_block.start_btn == 1) {
            dry_data_block.start_btn = 0;
        }
        else if(dry_data_block.start_btn == 2) {
            dry_data_block.start_btn = 0;
        }

        else if(dry_data_block.operation_mode == 1) {
            // operation switch가 heat로 선택되어져 있으면
            dry_data_block.debug_message = 'Choose an input mode';

            set_buzzer();

            core_interval = normal_interval * 10;
        }
        else {
            dry_data_block.cur_weight = 0.0;
            dry_data_block.ref_weight = 0.0;
            dry_data_block.pre_weight = 0.0;
            dry_data_block.tar_weight1 = 0.0;
            dry_data_block.tar_weight2 = 0.0;
            dry_data_block.tar_weight3 = 0.0;

            dry_data_block.state = 'input';

            dry_data_block.elapsed_time = 0;
        }

        if(dry_data_block.cum_weight > dry_data_block.cum_ref_weight) {
            dry_data_block.debug_message = 'Replace the catalyst';

            set_buzzer();

            core_interval = normal_interval * 10;
        }

        setTimeout(core_watchdog, core_interval);
    }

    else if(dry_data_block.state == 'input') {
        //히터오프
        //교반기오프
        //음식물 무게 측정
        // 목표 중량 계산?food에서 ? 여기에서 ?

        set_heater(0, 0, 0);
        set_stirrer(0);

        if(dry_data_block.start_btn == 1) {
            dry_data_block.start_btn = 0;
            if (dry_data_block.safe_door == 0) {
                if (dry_data_block.output_door == 0) {
                    if (dry_data_block.input_door == 0) {
                        if (dry_data_block.operation_mode == 1) {
                            // 스위치가 heat 모드로 되어 있다면

                            dry_data_block.ref_weight = dry_data_block.ref_weight + dry_data_block.cur_weight - dry_data_block.pre_weight;

                            dry_data_block.tar_weight1 = parseFloat(dry_data_block.ref_weight * 0.60).toFixed(1);
                            dry_data_block.tar_weight2 = parseFloat(dry_data_block.ref_weight * 0.30).toFixed(1);
                            dry_data_block.tar_weight3 = parseFloat(dry_data_block.ref_weight * 0.17).toFixed(1);

                            fs.writeFileSync('ddb.json', JSON.stringify(dry_data_block, null, 4), 'utf8');

                            dry_data_block.state = 'heat';

                            set_heater(1, 1, 1);
                            set_stirrer(1);

                            setTimeout(core_watchdog, normal_interval * 5);
                            return;
                        }
                        else {
                            dry_data_block.debug_message = 'Choose a heat mode';

                            set_buzzer();

                            core_interval = normal_interval * 10;
                        }
                    }
                    else {
                        dry_data_block.debug_message = 'Close the input door';

                        set_buzzer();

                        core_interval = normal_interval * 10;
                    }
                }
            }
        }
        else if(dry_data_block.start_btn == 2) {
            dry_data_block.start_btn = 0;
        }

        if(dry_data_block.debug_mode == 1) {
            dry_data_block.state = 'debug';
        }

        else if(dry_data_block.output_door == 1) {
            dry_data_block.debug_message = 'Close the output door';

            set_buzzer();

            core_interval = normal_interval * 10;
        }

        else if(dry_data_block.safe_door == 1) {
            dry_data_block.debug_message = 'Close the safe door';

            set_buzzer();

            core_interval = normal_interval * 10;
        }

        setTimeout(core_watchdog, core_interval);
    }

    else if(dry_data_block.state == 'heat') {

        // if(){//투입문, 배출게이트 닫혀있어야함
        //교반기 가동
        //MAX온도이상일때 히터오프
        //목표 중량 도달시 히터오프
        //
        // if(){//온도 40도 이하 체크
        //교반기 오프
        //종료 알람
        //상태 END로 변경
        // }
        // }
        // else{
        //히터 오프
        //교반기 오프
        // }
        // if(){//END 상태 //투입문 닫힘, 배출게이트 열림, 배출안전문 닫힘, 현 중량 0.2KG 이상

        // }
        // else{
        //교반기 동작 버튼 눌렀을때 교반기 온/오프 토글
        //if(){//현 중량 0.2kg이하일시
        //교반기 중지
        //}
        // }

        if(dry_data_block.start_btn == 1) {
            dry_data_block.start_btn = 0;
        }
        else if(dry_data_block.start_btn == 2) {
            dry_data_block.start_btn = 0;
        }

        if(dry_data_block.operation_mode == 0) {
            // 스위치가 input 모드로 되어 있다면

            dry_data_block.pre_weight = dry_data_block.cur_weight;

            fs.writeFileSync('ddb.json', JSON.stringify(dry_data_block, null, 4), 'utf8');

            dry_data_block.state = 'input';

            set_heater(0, 0, 0);
            set_stirrer(0);

            set_buzzer();

            setTimeout(core_watchdog, normal_interval * 5);
            return;
        }

        else if(dry_data_block.cur_weight <= dry_data_block.tar_weight1) {
            set_heater(1, 1, 0);
            set_stirrer(1);
        }

        else if(dry_data_block.cur_weight <= dry_data_block.tar_weight2) {
            set_heater(1, 0, 0);
            set_stirrer(1);
        }

        else if(dry_data_block.cur_weight <= dry_data_block.tar_weight3) {
            // 무게가 목표치에 도달하면

            dry_data_block.cum_weight += dry_data_block.ref_weight;

            dry_data_block.ref_weight = 0.0;
            dry_data_block.pre_weight = 0.0;
            dry_data_block.tar_weight1 = 0.0;
            dry_data_block.tar_weight2 = 0.0;
            dry_data_block.tar_weight3 = 0.0;

            fs.writeFileSync('ddb.json', JSON.stringify(dry_data_block, null, 4), 'utf8');

            dry_data_block.state = 'end';

            set_heater(0, 0, 0);
            set_stirrer(0);

            set_buzzer();

            setTimeout(core_watchdog, normal_interval * 10);
            return;
        }

        if(dry_data_block.output_door == 1 || dry_data_block.safe_door == 1 || dry_data_block.input_door == 1) {
            dry_data_block.debug_message = 'Exception';

            dry_data_block.state = 'exception';

            set_heater(0, 0, 0);
            set_stirrer(0);

            set_buzzer();

            setTimeout(core_watchdog, normal_interval * 5);
            return;
        }

        setTimeout(core_watchdog, core_interval);
    }

    else if(dry_data_block.state == 'end') {

        // if(){//투입문, 배출게이트 닫혀있어야함
        //교반기 가동
        //MAX온도이상일때 히터오프
        //목표 중량 도달시 히터오프
        //
        // if(){//온도 40도 이하 체크
        //교반기 오프
        //종료 알람
        //상태 END로 변경
        // }
        // }
        // else{
        //히터 오프
        //교반기 오프
        // }
        // if(){//END 상태 //투입문 닫힘, 배출게이트 열림, 배출안전문 닫힘, 현 중량 0.2KG 이상

        // }
        // else{
        //교반기 동작 버튼 눌렀을때 교반기 온/오프 토글
        //if(){//현 중량 0.2kg이하일시
        //교반기 중지
        //}
        // }

        set_heater(0, 0, 0);

        if(dry_data_block.start_btn == 1) {
            dry_data_block.start_btn = 0;
        }
        else if(dry_data_block.start_btn == 2) {
            dry_data_block.start_btn = 0;
        }

        if(dry_data_block.output_door == 0) {
            set_stirrer(0);
        }
        else if(dry_data_block.output_door == 1) {
            set_stirrer(1);
        }

        if(dry_data_block.cur_weight < 0.5) {
            if(dry_data_block.output_door == 0) {
                if(dry_data_block.safe_door == 0) {
                    if(dry_data_block.operation_mode == 0) {
                        // 스위치가 input 모드로 되어 있다면
                        set_heater(0, 0, 0);
                        set_stirrer(0);

                        set_buzzer();
                        dry_data_block.state = 'input';

                        dry_data_block.elapsed_time = 0;

                        setTimeout(core_watchdog, normal_interval * 5);
                        return;
                    }
                    else {
                        dry_data_block.debug_message = 'Choose an input mode';

                        core_interval = normal_interval * 10;
                    }
                }
                else {
                    dry_data_block.debug_message = 'Close the safe door';

                    core_interval = normal_interval * 10;
                }
            }
            else {
                dry_data_block.debug_message = 'Close the output door';

                core_interval = normal_interval * 10;
            }
        }
        else {
            dry_data_block.debug_message = 'Empty the contents';

            core_interval = normal_interval * 10;
        }

        setTimeout(core_watchdog, core_interval);
    }

    else if(dry_data_block.state == 'debug') {
        if(dry_data_block.start_btn == 1) {
            dry_data_block.start_btn = 0;
        }
        else if(dry_data_block.start_btn == 2) {
            dry_data_block.start_btn = 0;
        }

        if(dry_data_block.debug_mode == 0) {
            set_heater(0, 0, 0);
            set_stirrer(0);

            set_buzzer();

            dry_data_block.state = 'input';

            dry_data_block.elapsed_time = 0;

            setTimeout(core_watchdog, normal_interval * 10);
            return;
        }
        else {
            if(dry_data_block.cur_weight == dry_data_block.loadcell_ref_weight) {
                dry_data_block.debug_message = 'Complete Zero point';

            }
            else {
                dry_data_block.debug_message = 'Raise 10Kg weight';

                set_zero_point();
            }

            core_interval = normal_interval * 50;
        }

        setTimeout(core_watchdog, core_interval);
    }

    else if(dry_data_block.state == 'exception') {
        if(dry_data_block.start_btn == 1) {
            dry_data_block.start_btn = 0;
        }
        else if(dry_data_block.start_btn == 2) {
            dry_data_block.start_btn = 0;
        }

        if(dry_data_block.output_door == 1) {
            dry_data_block.debug_message = 'Close the output door';

            set_buzzer();

            core_interval = normal_interval * 10;
        }

        else if(dry_data_block.safe_door == 1) {
            dry_data_block.debug_message = 'Close the safe door';

            set_buzzer();

            core_interval = normal_interval * 10;
        }

        else if(dry_data_block.input_door == 1) {
            dry_data_block.debug_message = 'Close the input door';

            set_buzzer();

            core_interval = normal_interval * 10;
        }

        else if (dry_data_block.operation_mode == 1) {
            dry_data_block.debug_message = 'Choose an input mode';

            set_buzzer();

            core_interval = normal_interval * 10;
        }

        else if (dry_data_block.operation_mode == 0) {
            dry_data_block.pre_weight = dry_data_block.cur_weight;

            fs.writeFileSync('ddb.json', JSON.stringify(dry_data_block, null, 4), 'utf8');

            dry_data_block.state = 'input';

            set_heater(0, 0, 0);
            set_stirrer(0);

            set_buzzer();

            setTimeout(core_watchdog, normal_interval * 5);
            return;
        }

        setTimeout(core_watchdog, core_interval);
    }

    else {
        setTimeout(core_watchdog, core_interval);
    }

    //console.log('core watchdog');
}

///////////////////////////////////////////////////////////////////////////////

setTimeout(food_watchdog, first_interval);

function food_watchdog(){
    //100ms동작
    //실시간으로 변경되는상태값 저장
    //roadcell_lunch() //roadcell측정

    setTimeout(get_internal_temp, parseInt(Math.random()*10));
    setTimeout(get_input_door, parseInt(Math.random()*10));
    setTimeout(get_output_door, parseInt(Math.random()*10));
    setTimeout(get_safe_door, parseInt(Math.random()*10));
    setTimeout(get_weight, parseInt(Math.random()*10));
    setTimeout(get_operation_mode, parseInt(Math.random()*10));
    setTimeout(get_debug_mode, parseInt(Math.random()*10));
    setTimeout(get_start_btn, parseInt(Math.random()*10));

    setTimeout(food_watchdog, food_interval);

    //console.log('food watchdog');
}


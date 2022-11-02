var express = require('express');
var bodyParser = require('body-parser');
var app = express();
var exec = require('child_process').exec;
const { VK } = require('vk-io');
const { getRandomId } = require('vk-io')
const TelegramBot = require('node-telegram-bot-api');
const fs = require('fs');
const toml = require('toml');

const config = toml.parse(fs.readFileSync('../configuration.toml', 'utf-8'));
const KiberdedConfig = config.Kiberded;
const token_vk = KiberdedConfig.token;
const token_telegram = KiberdedConfig.token_telegram;

app.use(bodyParser.urlencoded({ extended: false }));
app.use(bodyParser.json());
app.use(express.static(__dirname + "/public"));

// todo: убрать токены в конфиг

const vk = new VK({
	token: token_vk
});


const telegram = new TelegramBot(token_telegram);


app.get('/webhook', function (req, res) {
    res.sendStatus(200);
	console.log('get /webhook');
});

app.get('/rubilovo', function (req, res) {
    res.sendFile(__dirname + "/" + "rubilovo.html");
    message_text = 'Кто-то рубанул деда.';
    const message = vk.api.messages.send({
			chat_id: 1,
			random_id: getRandomId(),
			message: message_text
		});
	const message_telegram = telegram.sendMessage(-1001668185586, message_text);
	exec('ded stop --basic',function (error, stdout, stderr) {
  			if (error) {
    			console.log(error.stack);
				console.log(`Error code: ${error.code}`);
				console.log(`Signal received: ${error.signal}`);
  			}
  		console.log(stdout);
  		console.log(`STDERR скрипта: ${stderr}`);
		});
	console.log(message_text);
});

app.get('/antirubilovo', function (req, res) {
    res.sendFile(__dirname + "/" + "antirubilovo.html");
	message_text = 'Кто-то перезагрузил деда.';
    const message = vk.api.messages.send({
			chat_id: 1,
			random_id: getRandomId(),
			message: message_text
		});
	const message_telegram = telegram.sendMessage(-1001668185586, message_text);
	exec('ded restart --all',function (error, stdout, stderr) {
  			if (error) {
    			console.log(error.stack);
				console.log(`Error code: ${error.code}`);
				console.log(`Signal received: ${error.signal}`);
  			}
  		console.log(stdout);
  		console.log(`STDERR скрипта: ${stderr}`);
		});
	console.log(message_text);
});

app.post('/webhook', function (req, res) {
	if (req.body.repository.name == "email-py") {
		branch_name = req.body.ref.split('/')[2];
		message_text = `Произошел гитхаб email-py в ${branch_name} юзером ${req.body.head_commit.author.name}: ${req.body.head_commit.message}`;
		const message = vk.api.messages.send({
			chat_id: 1,
			random_id: getRandomId(),
			message: message_text
		});
		const message_telegram = telegram.sendMessage(-1001668185586, message_text);
		console.log(message_text);
	}
	if (req.body.repository.name == "kiberded") {
		branch_name = req.body.ref.split('/')[2];
		message_text = `Произошел гитхаб деда в ${branch_name} юзером ${req.body.head_commit.author.name}: ${req.body.head_commit.message}`;
		const message = vk.api.messages.send({
			chat_id: 1,
			random_id: getRandomId(),
			message: message_text
		});
		const message_telegram = telegram.sendMessage(-1001668185586, message_text);
		exec('sh /root/kiberded/server/update.sh', function (error, stdout, stderr) {
			if (error) {
				console.log(error.stack);
				console.log(`Error code: ${error.code}`);
				console.log(`Signal received: ${error.signal}`);
			}
			console.log(stdout);
			console.log(`STDERR скрипта: ${stderr}`);
		});
		console.log(message_text);
	}
	if (req.body.repository.name ==  "magnetic-rectangles"){
		branch_name = req.body.ref.split('/')[2];
		message_text = `Произошел гитхаб магнитного в ${branch_name} юзером ${req.body.head_commit.author.name}: ${req.body.head_commit.message}`;
		const message = vk.api.messages.send({
			chat_id: 1,
			random_id: getRandomId(),
			message: message_text
		});
		const message_telegram = telegram.sendMessage(-1001668185586, message_text);
		console.log(message_text);
	}
});

app.listen(5000, function () {
	const message = vk.api.messages.send({
			chat_id: 1,
			random_id: getRandomId(),
			message: 'Обновляющий дед активирован'
		});
	const message_telegram = telegram.sendMessage(-1001668185586, 'Обновляющий дед активирован');
	console.log('update_daemon включен')
});

function execCallback(err, stdout, stderr) {
	if(stdout) console.log(stdout);
	if(stderr) console.log(stderr);
}

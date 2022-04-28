$(function() 
{
    /**
     * Init global variables
     */
    var sessionId = null
    var timer = null
    var timeout = 0
    var twoStage = true
    var temperatureDiffMax = null
    var pressureDiffMax = null

    // Constants
    const loopIntervalMs = 1000  // How often we request data from the sensors
    const speedOfSound = 343.2  // meters per second
    const diskMinusPortsPercentage = 0.55  // A rough estimate based on Tesla's patent drawings that ~ half of the disk is ports, spokes, or shaft >> should be part of rotor model?

    // Define models
    var rotorModel = {
        diskDiameter: 0,
        diskRadius: 0,
        diskThickness: 0,
        diskCount: 0,
        materialWeight: 0,
        diskSurfaceAreaGross: 0,
        diskSurfaceAreaNet: 0,
        diskVolume: 0,
        diskMass: 0,
        totalRotorMass: 0,
        diskCircumference: 0,
        rpmForSupersonic: 0,
    }

    var speedModel = {
        rpmMax: 0,
        rpmAvg: 0,
        acceleration: 0,
        accelerationMax: 0,
        angularVelocity: 0,
        peripherySpeed: 0,
        distanceTravelled: 0,
    }

    var powerModel = {
        inertia: 0,
        kineticEnergy: 0,
        centrifugalForce: 0,
    }

    var temperatureModel = {
        temperature: null,
        temperatureMin: null,
        temperatureMax: null,
    }

    var pressureModel = {
        pressure: null,
        pressureMin: null,
        pressureMax: null,
    }

    // Define main data model
    // Have to use Object.create() to create new models instead of references
    var dataModel = {
        rotor: [Object.create(rotorModel), Object.create(rotorModel)],
        speed: [Object.create(speedModel), Object.create(speedModel)],
        power: [Object.create(powerModel), Object.create(powerModel)],
        temperature: [Object.create(temperatureModel), Object.create(temperatureModel)],
        pressure: [Object.create(pressureModel), Object.create(pressureModel)],
    }

    /**
     * Create rpm chart
     */
    var rpmChart = new Chart('rpm-chart', {
        type: 'line',
        options: {
            scales: {
                y: {
                    ticks: {
                        color: '#95aac9',
                        callback: function(value) {
                            return (value / 1000) + 'k';  // Thousands of RPM 
                        }
                    },
                    grid: {
                        display: true,
                        color: "rgba(227,235,246,.1)",
                        borderDash: [2, 2]
                    }
                    //beginAtZero: true
                },
                x: {
                    //type: 'timeseries',
                    ticks: {
                        color: '#95aac9',
                        autoSkip: true,
                        maxTicksLimit: 20
                    },
                    grid: {
                        display: false
                    },
                    title: {
                        display: true,
                        text: 'Time (Seconds)',
                        color: '#95aac9',
                    }
                }
            },
            animation: {
                duration: 0
            },
            plugins: {
                legend: {
                    display: false,  // We're going to need to display a legend when we show 2 readings in one chart
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            }
        },
        data: {
            labels: [],
            datasets: [{
                label: 'RPM1',
                data: [],
                tension: 0.5,
                borderColor: '#2c7be5',
                backgroundColor: '#2c7be5',
            },{
                label: 'RPM2',
                data: [],
                tension: 0.5,
                borderColor: '#d2ddec',
                backgroundColor: '#d2ddec',
            }]
        }
    });


    /**
     * Open / close settings
     */
    $( "#settings-btn" ).on( "click", function() {
        $( ".sheet-overlay" ).addClass( "sheet-overlay-active" )
        $( ".sheet" ).addClass( "sheet-active" )
    })

    $( ".sheet-overlay, #settings-close-btn" ).on( "click", function() {
        $( ".sheet-overlay" ).removeClass( "sheet-overlay-active" )
        $( ".sheet" ).removeClass( "sheet-active" )
    })


    /**
     * Handle settings form changes
     * @param {string} units The units to set the values to (metric || imperial)
     */ 
    function setUnits(units)
    {
        if (units === "metric") {
            $("#settings-form .unit").text("mm")
            $("#settings-form #disk-diameter").prop("step", "1")
            $("#settings-form #disk-thickness").prop("step", "0.1")
        } else if (units === "imperial") {
            $("#settings-form .unit").text("in")
            $("#settings-form #disk-diameter").prop("step", "0.1")
            $("#settings-form #disk-thickness").prop("step", "0.01")
        }
    }


    function applySettings()
    {
        // Each time settings are changed, reset the dashboard
        reset()

        // Set global variables
        twoStage = $("#two-stage").is(":checked")
        
        for (let index = 0; index <= 1; index++) {
            let i = index === 1 ? "2" : ""

            let rotor = dataModel.rotor[index]

            rotor.diskDiameter = Number( $("#disk-diameter" + i).val() )
            rotor.diskRadius = rotor.diskDiameter / 2
            rotor.diskThickness = Number( $("#disk-thickness" + i).val() )
            rotor.diskCount = Number( $("#disk-count" + i).val() )
            rotor.materialWeight = Number( $("#disk-material" + i).val() )
            rotor.diskSurfaceAreaGross = Math.PI * rotor.diskRadius ** 2
            rotor.diskSurfaceAreaNet = rotor.diskSurfaceAreaGross * diskMinusPortsPercentage
            rotor.diskVolume = (rotor.diskSurfaceAreaNet * rotor.diskThickness) / 1000
            rotor.diskMass = rotor.materialWeight * rotor.diskVolume
            rotor.totalRotorMass = rotor.diskMass * rotor.diskCount
            rotor.diskCircumference = Math.max(Math.PI * rotor.diskDiameter, 0.001)  // Max to prevent division by zero errors
            rotor.rpmForSupersonic = (speedOfSound / rotor.diskCircumference) * 60000

            // Display values
            Object.keys(rotorModel).filter(element => element !== "diskMaterial").forEach(element => {
                $("#" + element + i).text( Math.round(rotor[element] * 100) / 100 )
            })
        }

        if (twoStage) {
            $(".two-stage").show()
        } else {
            $(".two-stage").hide()
        }

        // @TODO: reset graph? Else # of dataPoints might differ per stage
    }


    function saveSettings()
    {
        var  formData = []

        // Remove old formData
        localStorage.removeItem('settings')

        // Loop through form input fields
        $("#settings-form input[type=number], #settings-form input[type=checkbox], #settings-form select, #settings-form input[type=radio]:checked").each(function() {
            let value = null

            if ($(this).attr('type') === "radio") {
                value = this.id
            } else if ($(this).attr('type') === "checkbox") {
                value = $(this).is(":checked") ? true : false
            } else {
                value = this.value
            }
            
            formData.push({ 
                name: this.name, 
                value: value,
                type: $(this).attr('type')
            })
        })

        // Convert array to JSON and story in localStorage
        localStorage.settings = JSON.stringify(formData)
    }


    function loadSettings()
    {
        if (localStorage.settings != undefined) {
            settings  = JSON.parse(localStorage.settings)
            for (var i = 0; i < settings.length; i++) {
                if (settings[i].type != undefined && settings[i].type == "radio") {
                    $("#" + settings[i].value).prop('checked', true)
                } else if (settings[i].type != undefined && settings[i].type == "checkbox") {
                    $("[name=" + settings[i].name + "]").prop("checked", settings[i].value)
                } else {
                    $("[name=" + settings[i].name + "]").val(settings[i].value)
                }

                if (settings[i].name === "units")
                {
                    setUnits(settings[i].value)
                }
            }
        } else {
            setUnits("metric")
        }

        applySettings()
    }
    
    // Get form data from localstorage on page load
    loadSettings()

    // Listen for changes in the settings form
    $("#settings-form input, #settings-form select").on( "input", function() 
    {
        applySettings()

        // Don't save settings on every change immediately, but wait a little to batch them
        clearTimeout(timeout);

        timeout = setTimeout(function() {
            saveSettings()
        }, 2000)
    })

    $("#settings-form input[name=units]").on( "change", function() {
        setUnits(this.id)
    })


    /**
     * Reset all data in the dashboard to its initial state
     */
    function reset() 
    {
        // Reset all charts
        ticks = 0
        rpmChart.data.labels = []
        rpmChart.data.datasets.forEach((dataset) => {
            dataset.data = []  // Set to empty array
        })
        rpmChart.update()

        stopTimer(timer)
        $("#seconds").html('00')
        $("#minutes").html('00')

        temperatureDiffMax = null
        pressureDiffMax = null

        // Reset main data model
        dataModel = {
            rotor: [Object.create(rotorModel), Object.create(rotorModel)],
            speed: [Object.create(speedModel), Object.create(speedModel)],
            power: [Object.create(powerModel), Object.create(powerModel)],
            temperature: [Object.create(temperatureModel), Object.create(temperatureModel)],
            pressure: [Object.create(pressureModel), Object.create(pressureModel)],
        }
    }
    

    /**
     * Display sensor data on dashboard
     * 
     * @param {object} data JSON object containing one reading of all sensors
     */
    function displayData(data)
    {
        displayTemperature(data)
        displayPressure(data)

        $("#session-id").text(data.sessionId === null ? "No active session" : data.sessionId)

        if (sessionId === null && data.sessionId !== null) {
            // New session, so reset all charts and calculations
            applySettings()  // This also calls reset()
            timer = startTimer()
            
            displayRpm(data)
            displayPower(data)
        } else if (sessionId === null && data.sessionId === null) {
            // No session, don't update averages and other calculations, only live values
        } else if (sessionId !== null && data.sessionId === null) {
            // End session
            stopTimer(timer)
            timer = null
        } else {
            // Active session
            displayRpm(data)
            displayPower(data)
        }

        sessionId = data.sessionId
    }


    /**
     * Find the average of all numbers in an array 
     * 
     * @param {array} array Take the average of an array of data
     * @returns The average
     */
    function average(array) {
        return array.reduce((a, b) => (a + b)) / array.length;
    }


    /**
     * Round to two decimals with high precision
     * 
     * @see https://www.delftstack.com/howto/javascript/javascript-round-to-2-decimal-places/#using-the-custom-function-to-round-a-number-to2-decimal-places-in-javascript
     * @param {number} num Number we want to round
     */
    function roundToTwo(num) {
        return +(Math.round(num + "e+2")  + "e-2");
    }


    /**
     * Display RPM, update RPM chart, and calculate related values
     * 
     * @param {object} data JSON object containing one reading of all sensors 
     */
    function displayRpm(data)
    {
        // Update RPM chart
        const dataPoints = rpmChart.data.datasets[0].data.length
        let label = dataPoints * loopIntervalMs / 1000  // The x-axis label is the number of seconds since start of session, determined by number of data points * loop interval
        let rpmOld = dataPoints > 0 ? rpmChart.data.datasets[0].data[dataPoints - 1] : 0  // Grab the last RPM value in the data array
        rpmChart.data.labels.push(label)
        rpmChart.data.datasets[0].data.push(data.rpm)
        if (twoStage) { rpmChart.data.datasets[1].data.push(data.rpm2) }
        rpmChart.update()

        let stages = twoStage ? 2 : 1

        // Calculations
        for (let index = 0; index < stages; index++) {
            let i = index === 1 ? "2" : ""

            $('#card-rpm #rpm' + i).text( data['rpm' + i].toString().split(/(?=.{3}$)/).join(' ') )  // Add space to separate thousands

            let speed = dataModel.speed[index]
            let rotor = dataModel.rotor[index] 

            speed.rpmMax = Math.max(speed.rpmMax, data['rpm' + i])
            speed.rpmAvg = average(rpmChart.data.datasets[index].data)

            speed.peripherySpeed = (rotor.diskCircumference * data['rpm' + i]) / 60000
            let peripherySpeedOld = (rotor.diskCircumference * rpmOld) / 60000

            let accelerationOld = speed.acceleration.valueOf()
            speed.acceleration = (speed.peripherySpeed - peripherySpeedOld) / (loopIntervalMs / 1000)  // The acceleration between the last two data points
            speed.accelerationMax = Math.max(accelerationOld, speed.acceleration)

            speed.angularVelocity = (data['rpm' + i] / 60) * 2 * Math.PI
            speed.distanceTravelled = speed.distanceTravelled + (speed.peripherySpeed * (loopIntervalMs / 1000))  // Total distance the periphery has travelled in meters this session

            // Display the results of the calculations
            Object.keys(speedModel).forEach(element => {
                $("#" + element + i).text( Math.round(speed[element]) )
            })
        }
    }


    /**
     * Display temperature related data
     * 
     * @param {object} data JSON object containing one reading of all sensors 
     */
    function displayTemperature(data)
    {   
        for (let index = 0; index < dataModel.temperature.length; index++) {
            let i = index === 1 ? "2" : ""

            let currentTemperature = roundToTwo(data['temperature' + i])

            $("#card-temp #temperature" + i).html(currentTemperature + "&deg;C")  // @TODO: convert to Fahrenheit if Imperial is selected

            let temperature = dataModel.temperature[index]

            temperature.temperature = currentTemperature

            // Calculate
            temperature.temperatureMin = temperature.temperatureMin === null ? currentTemperature : Math.min(temperature.temperatureMin, currentTemperature)
            temperature.temperatureMax = temperature.temperatureMax === null ? currentTemperature : Math.max(temperature.temperatureMax, currentTemperature)

            // Display
            $("#temperatureMin" + i).text( temperature.temperatureMin )
            $("#temperatureMax" + i).text( temperature.temperatureMax )
        }

        var currentTemperatureDiff = Math.abs(dataModel.temperature[0].temperature - dataModel.temperature[1].temperature)
        temperatureDiffMax = temperatureDiffMax === null ? currentTemperatureDiff : Math.max(temperatureDiffMax, currentTemperatureDiff)
        $("#temperatureDiffMax").text( roundToTwo(temperatureDiffMax) )
    }


    /**
     * Display pressure related data
     * 
     * @param {object} data JSON object containing one reading of all sensors 
     */
    function displayPressure(data)
    {   
        for (let index = 0; index < dataModel.pressure.length; index++) {
            let i = index === 1 ? "2" : ""

            let currentPressure = roundToTwo(data['pressure' + i])

            $("#card-pressure #pressure" + i).html(currentPressure + " Psi")  // @TODO: convert to PSI if Imperial is selected

            let pressure = dataModel.pressure[index]

            pressure.pressure = currentPressure

            // Calculate
            pressure.pressureMin = pressure.pressureMin === null ? currentPressure : Math.min(pressure.pressureMin, currentPressure)
            pressure.pressureMax = pressure.pressureMax === null ? currentPressure : Math.max(pressure.pressureMax, currentPressure)

            // Display
            $("#pressureMin" + i).text( pressure.pressureMin )
            $("#pressureMax" + i).text( pressure.pressureMax )
        }

        var currentPressureDiff = Math.abs(dataModel.pressure[0].pressure - dataModel.pressure[1].pressure)
        pressureDiffMax = pressureDiffMax === null ? currentPressureDiff : Math.max(pressureDiffMax, currentPressureDiff)
        $("#pressureDiffMax").text( roundToTwo(pressureDiffMax) )
    }


    /**
     * Display Power related data
     * 
     * @param {object} data JSON object containing one reading of all sensors 
     */
    function displayPower(data)
    {   
        // TODO: Process Volts and Amps sensor readings

        // Calculations
        for (let index = 0; index < dataModel.power.length; index++) {
            let i = index === 1 ? "2" : ""

            let power = dataModel.power[index]
            let speed = dataModel.speed[index]
            let rotor = dataModel.rotor[index]
             
            // Calculate
            power.inertia = (0.5 * rotor.totalRotorMass * (rotor.diskRadius / 1000) ** 2)
            power.kineticEnergy = 0.5 * (power.inertia / 1000) * speed.angularVelocity ** 2
            power.centrifugalForce = (rotor.totalRotorMass / 1000) * (speed.angularVelocity ** 2) * (rotor.diskRadius / 1000)

            // Display
            $("#inertia" + i).text( Math.round(power.inertia * 1000000) / 1000000 )
            $("#kineticEnergy" + i).text( Math.round(power.kineticEnergy) )
            $("#centrifugalForce" + i).text( Math.round(power.centrifugalForce) )
        }
    }


    /**
     * Start a timer to count the duration of a session
     * 
     * @returns {object} The timer object 
     */
    function startTimer()
    {
        let seconds = 0
        function pad ( val ) { return val > 9 ? val : "0" + val; }
        return setInterval( function() {
            $("#seconds").html(pad(++seconds%60))
            $("#minutes").html(pad(parseInt(seconds/60,10)))
        }, 1000)
    }


    /**
     * Stop a timer
     * 
     * @param {object} timer The timer object
     */
    function stopTimer(timer)
    {
        clearInterval ( timer )
    }


    // Show / hide additional stats
    $("#more-stats-btn").on( "click", function() 
    {
        if ( $("#more-stats-btn .fe").hasClass("fe-eye") ) {
            console.log("hasClass fe-eye")
            $(".data-wrapper").hide()
            $("#more-stats-btn .fe").removeClass("fe-eye").addClass("fe-eye-off")
        } else {
            console.log("NOT hasClass fe-eye")
            $(".data-wrapper").show()
            $("#more-stats-btn .fe").removeClass("fe-eye-off").addClass("fe-eye")
        }
    })


    $("#valve-btn").on( "click", function() 
    {
        let currentState = $(this).data( "state" )
        let newState = !currentState

        openValve(newState)
    })


    /**
     * Open or close an electronic valve to start or stop a test session
     * 
     * @param {boolean} state True to open valve, false to close valve
     */
    function openValve(state)
    {
        // Show loading indicator
        $("#valve-btn .fe").removeClass("fe-play-circle").addClass("fe-clock")

        let request_data = {
            action: state === true ? "open_valve" : "close_valve"
        }

        $.ajax({
            type: "POST",
            url: "http://localhost:8000/valve",
            contentType: "json",
            dataType: "json",
            data: JSON.stringify(request_data),
            success: function(data, text)
            {
                console.log(data)

                // Update button state in Dashboard
                if (data.valveOpen === true)
                {
                    // Set button to opened state (show stop)
                    $("#valve-btn").data( "state", true )
                    $("#valve-btn .fe").removeClass("fe-clock").addClass("fe-stop-circle")
                } else {
                    // Set button to closed state (show play)
                    $("#valve-btn").data( "state", false )
                    $("#valve-btn .fe").removeClass("fe-stop-circle").addClass("fe-play-circle")
                }
            }, 
            error: function (request, status, error) {
                console.error(request.responseText)
                $("#valve-btn .fe").removeClass("fe-clock").removeClass("fe-stop-circle").addClass("fe-play-circle")
                $("#valve-btn").data( "state", false )
            },
        })
    }


    /**
     * This loop polls the Python sensor reading script every 500ms for new data
     */
    function loop() 
    {
        let request_data = {
            action: "read_sensors"
        }

        $.ajax({
            type: "POST",
            url: "http://localhost:8000/sensors",
            contentType: "json",
            dataType: "json",
            data: JSON.stringify(request_data),
            success: function(data, text)
            {
                console.log(data)

                // Update data in Dashboard
                displayData(data)
            }, 
            error: function (request, status, error) {
                console.error(request.responseText)
            },
        })

        setTimeout(loop, loopIntervalMs)
    }

    loop()
})
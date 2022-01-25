$(function() 
{
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

    function saveSettings()
    {
        var  formData = []

        // Remove old formData
        localStorage.removeItem('settings')

        // Loop through form input fields
        $("#settings-form input[type=number], #settings-form select, #settings-form input[type=radio]:checked").each(function() {
            formData.push({ 
                name: this.name, 
                value: $(this).attr('type') === "radio" ? this.id : this.value,
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
                if (settings[i].type != undefined && settings[i].type == "radio")
                {
                    $("#" + settings[i].value).prop('checked', true)
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
    }
    
    // Get form data from localstorage on page load
    loadSettings()

    // Listen for changes in the settings form
    let timeout = 0;

    $("#settings-form input, #settings-form select").on( "input", function() {
        // Don't save settings on every change immediately, but wait a little to batch them
        clearTimeout(timeout);

        timeout = setTimeout(function() {
            saveSettings()
        }, 3000)
    });

    $("#settings-form input[name=units]").on( "change", function() {
        setUnits(this.id)
    })


    /**
     * Create charts
     */
    rpmChart = new Chart('rpm-chart', {
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
                    ticks: {
                        color: '#95aac9',
                    },
                    grid: {
                        display: false
                    }
                }
            },
            plugins: {
                legend: {
                    display: false,  // We're going to need to display a legend when we show 2 readings in one chart
                }
            }
        },
        data: {
            labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
            datasets: [{
                label: 'Earned',
                data: [0, 1000, 5000, 15000, 10000, 20000, 15000, 25000, 20000, 30000, 25000, 40000],
                tension: 0.5,
                borderColor: '#2c7be5'
            }]
        }
    });


    /**
     * Reset all data in the dashboard to its initial state
     */
    function reset() 
    {
        // Reset all charts
        rpmChart.destroy()

        // Reset calculations like averages
    }


    let sessionId = null


    /**
     * Display sensor data on dashboard
     * 
     * @param {object} data JSON object containing one reading of all sensors
     */
    function displayData(data)
    {
        // How to handle averages? Can't loop through all items every 500ms
        // Should probably add up a total, and then read the length of the array so we know what to divide with

        if (sessionId === null && data.sessionId !== null)
        {
            // New session, so reset all charts and calculations
            reset()
        } else if (sessionId === null && data.sessionId === null)
        {
            // No session, don't update averages and other calculations, only live values
        } else if (sessionId !== null && data.sessionId === null)
        {
            // End session
        } else {
            // Active session
        }
    }


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
            url: "server.py",
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
            url: "server.py",
            contentType: "json",
            dataType: "json",
            data: JSON.stringify(request_data),
            success: function(data, text)
            {
                console.log(data)

                // Update data in Dashboard
                displayData(data)

                sessionId = data.sessionId
            }, 
            error: function (request, status, error) {
                console.error(request.responseText)
            },
        })

        setTimeout(loop, 5000)
    }

    loop()
})
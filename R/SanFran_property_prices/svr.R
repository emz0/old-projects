
library(RPostgreSQL)
library(neuralnet)
library(caTools)
library(e1071)


get_data <- function(id_district,from,to){
  drv <- dbDriver("PostgreSQL")
  con <- dbConnect(drv,host='localhost',port='5432',dbname='postgres',user='postgres',password='postgres')
  query <- paste("select a.month,  a.month_cos, a.month_sin, a.year, a.average_price from monthly_district_averages a
                 JOIN districts d ON a.district = d.pddistrict
                  WHERE d.id = '",id_district,"' and (a.year >= ",from," and a.year < ",to,")
                order by a.year,a.month  ",sep = "")
  rs <- dbSendQuery(con,query)
  data <- fetch(rs,n=-1)
  dbDisconnect(con)
  return(data)
  
}

normalize <- function(x) {
  return ((x - min(x)) / (max(x) - min(x)))
}

denormalize <- function(x,minval,maxval) {
  x*(maxval-minval) + minval
}

mapee <- function(y, yhat){
  100*mean(abs((y - yhat)/y))
}

rmsee <- function(y,y_pred){
  return(sqrt(mean((y-y_pred)^2)))
}

k = 10

regression_types <- list("nu-regression")
kernel_types <- list("radial")
epsilons <- list(0.1)


for (l in 1:length(epsilons)){
  for (k in 1:length(kernel_types)){
    for (j in 1:length(regression_types)){
            
      error <- c()
      pr.nn <- NULL
      test <- NULL
      train <- NULL
      mape <- c()
      rmse <- c()
      mape_district <- c()
      rmse_district <- c()
     
      d_predictions <- list()
      set.seed(101) 
      for(d_id in 1:10){
        d <- get_data(d_id,2008,2016)
       
        
        for(i in 1:k){
          data <- d
          d_pred <- list()
          data$average_price_max <- max(data$average_price)
          data$average_price_min <- min(data$average_price)
          data$average_price <- normalize(data$average_price)
          
          data$year_max <- max(data$year)
          data$year_min <- min(data$year)
          data$year <- normalize(data$year)
          
        
          sample <- sample.int(nrow(data), floor(.75*nrow(data)), replace = F)
          train <- data[sample, ]
          test <- data[-sample, ]
          
          traininginput <- list()
          traininginput$year <-  train$year
          traininginput$month_cos <-  train$month_cos
          traininginput$month_sin <-  train$month_sin
          traininginput$output <- train$average_price
         
          model <- svm(output ~ year+month_cos+month_sin,traininginput,type=regression_types[j],kernel=kernel_types[k],epsilon=epsilons[l])
          testdata <- subset(test, select = c("month_cos","month_sin","year","average_price","month"))
          
          predictedY <- predict(model, testdata[1:3])
          
          predictedY <- denormalize(predictedY,data$average_price_min[1],data$average_price_max[1])
          testdata$average_price <-denormalize(testdata$average_price,data$average_price_min[1],data$average_price_max[1])
         
          mape[i] <- mapee(testdata$average_price,predictedY)
          rmse[i] <- rmsee(testdata$average_price,predictedY)
         
      
        }
        mape_district[d_id] <- mean(mape)
        rmse_district[d_id] <- mean(rmse)
        print(paste("MAPE PRE DISTRIKT ",d_id,": ",mape_district[d_id]))
        print(paste("RMSE PRE DISTRIKT ",d_id,": ",rmse_district[d_id]))
      }
      
      print(paste("Priemerne MAPE pre ",length(mape_district)," districtov s typom regresie ",regression_types[j]," s kernelom ",kernel_types[k]," s epsilonom ",epsilons[l],": ",mean(mape_district),"%",sep=""))
      print(paste("Priemerne RMSE pre ",length(rmse_district)," districtov s typom regresie ",regression_types[j]," s kernelom ",kernel_types[k]," s epsilonom ",epsilons[l],": ",mean(rmse_district),"",sep=""))
      
      }
  }
}


